# SPDX-License-Identifier: GPL-3.0-only
"""Reloj de la barra del escritorio y, al pulsarlo, el calendario de las tareas de las notas.

Los días con tareas salen resaltados; al elegir uno se listan y un clic abre la nota.
«Nueva tarea» crea la nota con fecha en Tareas/ del proyecto que se ve (o de la raíz)."""
import datetime

from PySide6.QtCore import QDate, QLocale, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QTextCharFormat
from PySide6.QtWidgets import (QCalendarWidget, QHBoxLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QVBoxLayout, QWidget, QWidgetAction)

from . import agenda

SPANISH = QLocale(QLocale.Language.Spanish, QLocale.Country.Spain)


def clock_text(now):
    """«15:52 · jue 5 nov»: hora grande y fecha corta, sin punto en las abreviaturas."""
    day = SPANISH.toString(now.date(), 'ddd d MMM').replace('.', '')
    return f'{now.strftime("%H:%M")}  ·  {day}'


def day_heading(day, today):
    if day == today:
        prefix = 'Hoy, '
    elif day == today + datetime.timedelta(days=1):
        prefix = 'Mañana, '
    elif day == today - datetime.timedelta(days=1):
        prefix = 'Ayer, '
    else:
        prefix = ''
    text = SPANISH.toString(QDate(day.year, day.month, day.day), 'dddd d \'de\' MMMM')
    return (prefix + text) if prefix else text[:1].upper() + text[1:]


class CalendarPanel(QWidget):
    def __init__(self, shell, close):
        super().__init__()
        self.shell, self.close_menu = shell, close
        self.days = {}
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self); layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(8)
        self.calendar = QCalendarWidget()
        self.calendar.setLocale(SPANISH)
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
        self.calendar.setGridVisible(False)
        self.calendar.setAccessibleName('Calendario de tareas')
        self.calendar.selectionChanged.connect(self.show_day)
        self.calendar.currentPageChanged.connect(lambda *_: self.mark_days())
        layout.addWidget(self.calendar)
        self.heading = QLabel(); self.heading.setWordWrap(True)
        self.heading.setStyleSheet('font-size: 15px; font-weight: bold;'); layout.addWidget(self.heading)
        self.items = QListWidget(); self.items.setAccessibleName('Tareas del día')
        self.items.setMinimumHeight(120)
        self.items.itemActivated.connect(self.open_item); self.items.itemClicked.connect(self.open_item)
        layout.addWidget(self.items)
        row = QHBoxLayout()
        today = QPushButton('Hoy'); today.clicked.connect(self.go_today); row.addWidget(today)
        row.addStretch()
        add = QPushButton('Nueva tarea…'); add.clicked.connect(self.new_task); row.addWidget(add)
        layout.addLayout(row)

    def refresh(self):
        """Relee las tareas (el índice de la bóveda ya está en memoria) y vuelve a hoy."""
        vault = self.shell.vault
        self.days = agenda.by_day(agenda.tasks(vault.note_index()[0], vault.root))
        self.go_today()

    def go_today(self):
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.calendar.setCurrentPage(today.year(), today.month())
        self.mark_days(); self.show_day()

    def mark_days(self):
        """Días sin nada en tono apagado; con tareas pendientes, en negrita y color de acento;
        con todo hecho, tachados. Hoy, subrayado."""
        colors = self.shell.colors
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())  # limpia el mes anterior
        plain = QTextCharFormat(); plain.setForeground(QColor(colors.muted))
        for weekday in Qt.DayOfWeek:
            self.calendar.setWeekdayTextFormat(weekday, plain)
        header = QTextCharFormat(); header.setForeground(QColor(colors.muted))
        header.setBackground(QColor(colors.panel)); header.setFontPointSize(8)
        self.calendar.setHeaderTextFormat(header)
        pending, done = QTextCharFormat(), QTextCharFormat()
        pending.setFontWeight(QFont.Weight.Bold); pending.setForeground(QColor(colors.accent))
        done.setForeground(QColor(colors.muted)); done.setFontStrikeOut(True)
        formats = {}
        for day, found in self.days.items():
            formats[day] = pending if any(not t.done for t in found) else done
            self.calendar.setDateTextFormat(QDate(day.year, day.month, day.day), formats[day])
        today = QTextCharFormat(formats.get(datetime.date.today(), plain))
        today.setFontUnderline(True); today.setFontWeight(QFont.Weight.Bold); today.setForeground(QColor(colors.text))
        self.calendar.setDateTextFormat(QDate.currentDate(), today)

    def selected_day(self):
        return self.calendar.selectedDate().toPython()

    def show_day(self):
        day = self.selected_day()
        found = self.days.get(day, [])
        pending = sum(not t.done for t in found)
        self.heading.setText(day_heading(day, datetime.date.today()) +
                             (f'  ·  {pending} pendiente' + ('s' if pending != 1 else '') if pending else ''))
        self.items.clear()
        for task in found:
            text = ('✓ ' if task.done else '○ ') + task.title + (f'   ·   {task.project}' if task.project else '')
            item = QListWidgetItem(text); item.setData(Qt.ItemDataRole.UserRole, str(task.path))
            item.setToolTip(str(task.path.relative_to(self.shell.vault.root)))
            if task.done:
                item.setForeground(QColor(self.shell.colors.muted))
            self.items.addItem(item)
        if not found:
            empty = QListWidgetItem('Nada con fecha este día.'); empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.items.addItem(empty)

    def open_item(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.close_menu()
            self.shell.open_note(path)

    def new_task(self):
        day = self.selected_day()
        self.close_menu()
        title, ok = QInputDialog.getText(self.shell, 'Nueva tarea',
                                         f'Tarea para el {day_heading(day, datetime.date.today()).lower()}:')
        if not ok or not title.strip():
            return
        vault = self.shell.vault
        project = self.shell.current_project() if self.shell.folder == vault.root else self.shell.folder
        base = project or vault.root
        try:
            folder = base / 'Tareas'
            if not folder.exists():
                vault.create_folder(base, 'Tareas')
            path = vault.child_path(folder, agenda.note_name(day, title.strip()), note=True)
            with path.open('x', encoding='utf-8') as handle:
                handle.write(agenda.note_text(day, title.strip()))
            vault.forget_index()
        except (OSError, ValueError) as error:
            self.shell.status.setText('No se ha podido crear la tarea: ' + str(error)); return
        self.shell.status.setText('Tarea creada en ' + str(path.relative_to(vault.root)))
        self.shell.open_note(path, edit=True)


class ClockButton(QPushButton):
    """La hora en la barra; se pone al día al cambiar el minuto, no cada segundo."""

    def __init__(self, shell):
        super().__init__()
        self.shell = shell
        self.setObjectName('clock')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName('Reloj y calendario')
        self.setToolTip('Calendario con las tareas de tus notas')
        self.menu = QMenu(self)
        self.panel = CalendarPanel(shell, self.menu.close)
        action = QWidgetAction(self.menu); action.setDefaultWidget(self.panel); self.menu.addAction(action)
        self.menu.aboutToShow.connect(self.panel.refresh)
        self.clicked.connect(self.open_calendar)
        self.timer = QTimer(self, singleShot=True, timeout=self.tick)
        self.restyle()
        self.tick()

    def restyle(self):
        c = self.shell.colors
        self.menu.setStyleSheet(f'QMenu {{ background: {c.panel}; border: 1px solid {c.border}; padding: 4px; }}')
        self.panel.calendar.setStyleSheet(
            f'QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {c.card}; border-radius: 6px; }}'
            f'QCalendarWidget QToolButton {{ color: {c.text}; background: transparent; padding: 4px 8px; }}'
            f'QCalendarWidget QToolButton:hover {{ background: {c.hover}; border-radius: 6px; }}'
            f'QCalendarWidget QAbstractItemView {{ background: {c.panel}; color: {c.text}; '
            f'selection-background-color: {c.accent}; selection-color: {c.base}; outline: 0; }}'
            f'QCalendarWidget QAbstractItemView:disabled {{ color: {c.muted}; }}')

    def tick(self):
        now = datetime.datetime.now()
        self.setText(clock_text(now))
        # Siguiente cambio de minuto (+ medio segundo de margen); tras suspender se corrige solo.
        self.timer.start(max(500, (60 - now.second) * 1000 - now.microsecond // 1000 + 500))

    def open_calendar(self):
        if not self.menu.isVisible():
            self.menu.popup(self.mapToGlobal(QPoint(self.width() - self.menu.sizeHint().width(), self.height())))
