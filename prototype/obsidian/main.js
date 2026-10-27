const { Plugin, ItemView, Modal, FuzzySuggestModal, Menu, TFile, TFolder, Notice, setIcon, normalizePath } = require('obsidian');
const TYPE = 'project-desktop';
const DEFAULT_FOLDER = 'Escritorio Obsidian';
const WALLPAPER = /^wallpaper\.(png|jpe?g|webp|avif)$/i;
const PALETTES = {
  'Diseño': { hue: 345, saturation: 36, name: 'Burdeos textil', icon: 'shirt' },
  'Comunidad': { hue: 30, saturation: 36, name: 'Tierra medieval', icon: 'swords' },
  'Comunidad/Club': { hue: 38, saturation: 32, name: 'Madera y ámbar', icon: 'users' },
  'Diario': { hue: 34, saturation: 22, name: 'Papel y sepia', icon: 'notebook' },
  'Portfolio': { hue: 23, saturation: 32, name: 'Cobre', icon: 'briefcase' },
  'Naturaleza': { hue: 92, saturation: 28, name: 'Oliva', icon: 'sprout' },
  'Escritorio Obsidian': { hue: 145, saturation: 22, name: 'Bosque', icon: 'panels-top-left' },
  'Robótica': { hue: 181, saturation: 25, name: 'Petróleo', icon: 'bot' },
  'Diseño 3D': { hue: 207, saturation: 34, name: 'Azul técnico', icon: 'box' },
  'Archivo': { hue: 213, saturation: 21, name: 'Pizarra', icon: 'archive' },
  'Formación': { hue: 225, saturation: 30, name: 'Índigo', icon: 'graduation-cap' },
  'Vídeo': { hue: 345, saturation: 25, name: 'Burdeos', icon: 'clapperboard' }
};
const visible = f => !f.path.split('/').some(p => p.startsWith('.'));
const isPython = f => f instanceof TFile && f.extension.toLowerCase() === 'py';
const displayName = f => (isPython(f) ? f.name : f.basename || f.name).replace(/^\d+(?:\.\d+)?\s*[-–]\s*/, '');
const fileIcon = f => f instanceof TFolder ? 'folder' : isPython(f) ? 'file-code' : f.extension === 'canvas' ? 'layout-dashboard' : 'file-text';
const sorted = files => files.filter(visible).sort((a, b) => Number(b instanceof TFolder) - Number(a instanceof TFolder) || a.name.localeCompare(b.name, 'es', { numeric: true }));
const searchText = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');

class ApplicationsModal extends Modal {
  constructor(app, plugin) { super(app); this.plugin = plugin; this.query = ''; }
  onOpen() {
    this.modalEl.addClass('pd-manager');
    this.titleEl.setText('Aplicaciones');
    this.contentEl.createEl('p', { text: 'Busca una aplicación y ábrela. Usa la estrella para fijarla en la barra del escritorio.' });
    const toolbar = this.contentEl.createDiv('pd-manager-toolbar');
    const input = toolbar.createEl('input', { attr: { type: 'search', placeholder: 'Buscar aplicaciones…', 'aria-label': 'Buscar aplicaciones' } });
    input.oninput = () => { this.query = input.value; this.renderResults(); };
    this.refreshButton = this.plugin.button(toolbar, 'Actualizar lista', 'refresh-cw', async () => {
      this.refreshButton.disabled = true;
      this.status.setText('Buscando aplicaciones instaladas…');
      try { await this.plugin.refreshApplications(); this.renderResults(); }
      catch (error) { this.status.setText(error.message); }
      finally { this.refreshButton.disabled = false; }
    });
    this.status = this.contentEl.createEl('p', { cls: 'pd-manager-status', attr: { role: 'status', 'aria-live': 'polite' } });
    this.results = this.contentEl.createDiv('pd-manager-list');
    this.renderResults(); input.focus();
  }
  renderResults() {
    const p = this.plugin;
    const terms = searchText(this.query).split(/\s+/).filter(Boolean);
    const apps = p.applications.filter(app => terms.every(term => searchText([app.name, app.description, ...(app.keywords || [])].join(' ')).includes(term)))
      .sort((a, b) => Number(p.settings.favoriteApps.includes(b.id)) - Number(p.settings.favoriteApps.includes(a.id)) || a.name.localeCompare(b.name, 'es'));
    this.status.setText(`${apps.length} aplicaciones${apps.length ? ' · Favoritas primero' : ' · Prueba otro nombre o actualiza la lista'}`);
    this.results.empty();
    for (const app of apps) {
      const row = this.results.createDiv('pd-manager-row');
      const launch = p.button(row, app.name, 'app-window', async () => {
        launch.disabled = true; this.status.setText(`Abriendo ${app.name}…`);
        try { await p.launchApplication(app.id); this.close(); }
        catch (error) { this.status.setText(error.message); launch.disabled = false; }
      });
      launch.addClass('pd-manager-name'); launch.title = app.description;
      row.createEl('small', { text: app.description, cls: 'pd-manager-detail' });
      const pinned = p.settings.favoriteApps.includes(app.id);
      const favorite = p.button(row, pinned ? 'Desfijar' : 'Fijar', 'star', async () => {
        const next = pinned ? p.settings.favoriteApps.filter(id => id !== app.id) : [...p.settings.favoriteApps, app.id];
        try {
          await p.saveData({ ...p.settings, favoriteApps: next });
          p.settings.favoriteApps = next;
          this.renderResults();
          for (const leaf of this.app.workspace.getLeavesOfType(TYPE)) leaf.view.render();
        } catch (error) { this.status.setText('No se pudo guardar: ' + error.message); }
      });
      favorite.setAttribute('aria-label', `${pinned ? 'Desfijar' : 'Fijar'} ${app.name}`);
      favorite.setAttribute('aria-pressed', String(pinned));
    }
  }
  onClose() { this.contentEl.empty(); }
}

class VaultExplorerModal extends Modal {
  constructor(app, plugin, folder) { super(app); this.plugin = plugin; this.folder = folder; this.query = ''; this.page = 0; }
  onOpen() {
    this.modalEl.addClass('pd-manager');
    this.titleEl.setText('Explorar bóveda');
    const nav = this.contentEl.createDiv('pd-manager-toolbar');
    this.up = this.plugin.button(nav, 'Subir', 'arrow-up', () => this.navigate(this.folder.parent));
    this.plugin.button(nav, 'Raíz de la bóveda', 'home', () => this.navigate(this.app.vault.getRoot()));
    this.plugin.button(nav, 'Ver mapa', 'panels-top-left', async () => { await this.plugin.openFolder(this.folder.path); this.close(); });
    this.location = this.contentEl.createEl('p', { cls: 'pd-manager-location' });
    this.input = this.contentEl.createEl('input', { cls: 'pd-manager-search', attr: { type: 'search', placeholder: 'Buscar en esta carpeta y subcarpetas…', 'aria-label': 'Buscar archivos y carpetas' } });
    this.input.oninput = () => { this.query = this.input.value; this.page = 0; this.selected = null; this.renderResults(); };
    const actions = this.contentEl.createDiv('pd-manager-toolbar');
    this.plugin.button(actions, 'Nueva carpeta', 'folder-plus', () => this.plugin.createFolder(this.folder));
    this.plugin.button(actions, 'Nueva nota', 'file-plus', () => { this.plugin.createNote(this.folder); this.close(); });
    this.actionButtons = [
      this.plugin.button(actions, 'Renombrar', 'pencil', () => this.act(file => this.app.fileManager.promptForFileRename(file))),
      this.plugin.button(actions, 'Mover a…', 'folder-input', () => this.act(file => new MoveFileModal(this.app, file).open())),
      this.plugin.button(actions, 'Eliminar…', 'trash-2', () => this.act(file => this.app.fileManager.promptForDeletion(file)))
    ];
    this.selection = this.contentEl.createEl('p', { cls: 'pd-manager-status', attr: { role: 'status' } });
    this.results = this.contentEl.createDiv('pd-manager-list');
    this.pager = this.contentEl.createDiv('pd-manager-toolbar');
    this.events = ['create', 'delete', 'rename'].map(event => this.app.vault.on(event, () => {
      if (this.app.vault.getAbstractFileByPath(this.folder.path) !== this.folder) this.folder = this.app.vault.getRoot();
      if (this.selected && this.app.vault.getAbstractFileByPath(this.selected.path) !== this.selected) this.selected = null;
      this.renderResults();
    }));
    this.renderResults(); this.input.focus();
  }
  navigate(folder) {
    if (!folder) return;
    this.folder = folder; this.selected = null; this.query = ''; this.input.value = ''; this.page = 0;
    this.renderResults();
  }
  async act(callback) {
    if (!this.selected) return;
    try { await callback(this.selected); }
    catch (error) { new Notice('No se pudo completar la acción: ' + error.message); }
  }
  updateSelection() {
    this.selection.setText(this.selected ? `Seleccionado: ${this.selected.path}` : 'Selecciona un elemento para renombrarlo, moverlo o eliminarlo. Doble clic o Intro para abrir.');
    this.actionButtons.forEach(button => { button.disabled = !this.selected; });
    for (const row of this.results.children) row.classList.toggle('is-selected', row.dataset.path === this.selected?.path);
  }
  renderResults() {
    const root = this.app.vault.getRoot();
    this.location.setText(this.folder === root ? 'Bóveda · inicio' : this.folder.path);
    this.up.disabled = this.folder === root;
    const terms = searchText(this.query).split(/\s+/).filter(Boolean);
    const prefix = this.folder === root ? '' : this.folder.path + '/';
    const files = sorted(terms.length ? this.app.vault.getAllLoadedFiles().filter(file => file !== root && file.path.startsWith(prefix) && terms.every(term => searchText(file.path.slice(prefix.length)).includes(term))) : this.folder.children);
    if (this.selected && !files.includes(this.selected)) this.selected = null;
    const size = 60;
    this.page = Math.max(0, Math.min(this.page, Math.ceil(files.length / size) - 1));
    this.results.empty(); this.pager.empty();
    for (const file of files.slice(this.page * size, (this.page + 1) * size)) {
      const row = this.results.createDiv('pd-manager-row'); row.dataset.path = file.path;
      const open = () => {
        if (file instanceof TFolder) this.navigate(file);
        else { this.plugin.openNote(file); this.close(); }
      };
      const select = this.plugin.button(row, file.name, fileIcon(file), () => { this.selected = file; this.updateSelection(); });
      select.addClass('pd-manager-name'); select.ondblclick = open;
      select.onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); open(); } };
      row.createEl('small', { cls: 'pd-manager-detail', text: terms.length ? file.path : file instanceof TFolder ? `${file.children.filter(visible).length} elementos` : file.extension.toUpperCase() });
      this.plugin.button(row, 'Abrir', file instanceof TFolder ? 'folder-open' : 'arrow-up-right', open);
      this.plugin.bindFileMenu(row, file);
    }
    if (!files.length) this.results.createEl('p', { text: terms.length ? 'No hay resultados para esta búsqueda.' : 'Esta carpeta está vacía. Crea una nota o una subcarpeta.' });
    const previous = this.plugin.button(this.pager, 'Anterior', 'chevron-left', () => { this.page--; this.renderResults(); }); previous.disabled = this.page === 0;
    this.pager.createSpan({ text: `${files.length} elementos · Página ${this.page + 1} de ${Math.max(1, Math.ceil(files.length / size))}` });
    const next = this.plugin.button(this.pager, 'Siguiente', 'chevron-right', () => { this.page++; this.renderResults(); }); next.disabled = (this.page + 1) * size >= files.length;
    this.updateSelection();
  }
  onClose() { for (const event of this.events || []) this.app.vault.offref(event); this.contentEl.empty(); }
}

class NewFolderModal extends Modal {
  constructor(app, plugin, folder) { super(app); this.plugin = plugin; this.folder = folder; }
  onOpen() {
    this.titleEl.setText('Nueva carpeta');
    this.contentEl.createEl('p', { text: `Dentro de: ${this.folder.path || 'Bóveda inicio'}` });
    const form = this.contentEl.createEl('form');
    const label = form.createEl('label', { text: 'Nombre de la carpeta' });
    const input = label.createEl('input', { attr: { type: 'text', placeholder: 'Prácticas de clases', required: '', autocomplete: 'off' } });
    input.style.width = '100%';
    const error = form.createEl('p', { attr: { role: 'alert' } });
    const actions = form.createDiv('modal-button-container');
    this.plugin.button(actions, 'Cancelar', null, () => this.close());
    const submit = actions.createEl('button', { cls: 'mod-cta', text: 'Crear carpeta', attr: { type: 'submit' } });
    form.onsubmit = async e => {
      e.preventDefault();
      if (submit.disabled) return;
      const name = input.value.trim();
      if (!name || name.startsWith('.') || /[\\/:*?"<>|\x00-\x1f]/.test(name) || name.endsWith('.')) {
        error.setText('Escribe un nombre sin barras ni caracteres especiales y que no empiece ni termine con un punto.');
        input.focus(); return;
      }
      const path = normalizePath([this.folder.path === '/' ? '' : this.folder.path, name].filter(Boolean).join('/'));
      if (this.app.vault.getAbstractFileByPath(path)) {
        error.setText('Ya existe un archivo o una carpeta con ese nombre.'); input.focus(); return;
      }
      submit.disabled = true;
      try {
        await this.app.vault.createFolder(path);
      } catch (err) {
        error.setText('No se pudo crear la carpeta: ' + err.message);
        submit.disabled = false; return;
      }
      this.close();
      try { await this.plugin.openFolder(path); }
      catch (err) { new Notice('La carpeta se ha creado, pero no se pudo abrir: ' + err.message); }
    };
    input.focus();
  }
  onClose() { this.contentEl.empty(); }
}

class MoveFileModal extends FuzzySuggestModal {
  constructor(app, file) { super(app); this.file = file; this.setPlaceholder(`Mover «${file.name}» a…`); }
  getItems() {
    const file = this.file;
    return [this.app.vault.getRoot(), ...this.app.vault.getAllLoadedFiles().filter(f => f instanceof TFolder && f !== this.app.vault.getRoot() && visible(f))]
      .filter(f => f !== file.parent && f !== file && !(file instanceof TFolder && f.path.startsWith(file.path + '/')))
      .sort((a, b) => a.path.localeCompare(b.path, 'es'));
  }
  getItemText(folder) { return !folder.path || folder.path === '/' ? 'Bóveda inicio (raíz)' : folder.path; }
  async onChooseItem(folder) {
    const path = normalizePath([folder.path === '/' ? '' : folder.path, this.file.name].filter(Boolean).join('/'));
    if (this.app.vault.getAbstractFileByPath(path)) { new Notice('Ya existe un archivo o una carpeta con ese nombre en el destino.'); return; }
    try { await this.app.fileManager.renameFile(this.file, path); }
    catch (err) { new Notice('No se pudo mover: ' + err.message); }
  }
}

class DesktopView extends ItemView {
  constructor(leaf, plugin) { super(leaf); this.plugin = plugin; this.folderPath = plugin.settings.folder; this.page = 0; }
  getViewType() { return TYPE; }
  getDisplayText() { return `Escritorio · ${this.folderPath.split('/').pop() || 'inicio'}`; }
  getIcon() { return 'panels-top-left'; }
  getState() { return { folder: this.folderPath }; }
  async setState(state, result) {
    if (typeof state?.folder === 'string') this.folderPath = state.folder;
    this.page = 0;
    await super.setState(state, result);
    this.render();
  }
  async onOpen() { this.render(); }
  async onClose() { this.plugin.refreshVisibility(); }
  onResize() { this.plugin.clampWindows(); }
  render() {
    const p = this.plugin;
    const folder = p.folder(this.folderPath);
    if (!folder) { this.contentEl.empty(); this.contentEl.createEl('p', { text: 'La carpeta se ha movido. Abre otra desde Carpetas.' }); return; }
    this.contentEl.empty(); this.contentEl.addClass('pd-desktop');
    p.applyWallpaper(this.contentEl, folder);
    const header = this.contentEl.createDiv('pd-project-header');
    const titles = header.createDiv();
    titles.createDiv({ cls: 'pd-eyebrow', text: 'ESCRITORIO DE PROYECTOS' });
    titles.createEl('h1', { text: folder.name || 'inicio' });
    titles.createDiv({ cls: 'pd-breadcrumb', text: folder.path || 'Bóveda inicio' });
    const nav = header.createDiv('pd-header-actions');
    if (folder.parent) p.button(nav, 'Subir', 'arrow-up', () => p.openFolder(folder.parent.path));
    p.button(nav, 'Carpetas', 'panel-left', () => p.showDrawer(true));
    p.button(nav, 'Explorar bóveda', 'folder-search', () => p.openExplorer(folder));
    p.button(nav, 'Nueva carpeta', 'folder-plus', () => p.createFolder(folder));
    p.button(nav, 'Nueva nota', 'file-plus', () => p.createNote(folder));
    const entries = sorted(folder.children).filter(f => f instanceof TFolder || (f instanceof TFile && !WALLPAPER.test(f.name)));
    const pageSize = 8;
    this.page = Math.max(0, Math.min(this.page, Math.ceil(entries.length / pageSize) - 1));
    const current = entries.slice(this.page * pageSize, (this.page + 1) * pageSize);
    const map = this.contentEl.createDiv({ cls: 'pd-map', attr: { 'aria-label': 'Mapa del proyecto', role: 'group' } });
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 1000 600'); svg.setAttribute('preserveAspectRatio', 'none');
    svg.classList.add('pd-connections'); map.append(svg);
    const center = map.createDiv('pd-center');
    const icon = center.createSpan('pd-center-icon'); setIcon(icon, 'folder-open');
    center.createEl('strong', { text: folder.name || 'inicio' });
    center.createSpan({ text: `${entries.length} archivos y carpetas` });
    current.forEach((file, i) => {
      const angle = -Math.PI / 2 + i * 2 * Math.PI / Math.max(current.length, 1);
      const x = 500 + Math.cos(angle) * 350, y = 300 + Math.sin(angle) * 225;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M500 300 Q${(x + 500) / 2} 300 ${x} ${y}`); svg.append(path);
      const b = map.createEl('button', { cls: 'pd-map-node', attr: { 'data-path': file.path, title: file.path } });
      b.style.left = `${x / 10}%`; b.style.top = `${y / 6}%`;
      const iEl = b.createSpan('pd-node-icon'); setIcon(iEl, fileIcon(file));
      b.createSpan({ text: displayName(file) });
      b.createEl('small', { text: file instanceof TFolder ? `${file.children.filter(visible).length} elementos · abrir carpeta` : isPython(file) ? 'Abrir en VSCodium' : 'Abrir nota' });
      b.onclick = () => file instanceof TFolder ? p.openFolder(file.path) : p.openNote(file, this);
      p.bindFileMenu(b, file, this);
    });
    if (entries.length > pageSize) {
      const pager = this.contentEl.createDiv('pd-map-pager');
      const back = p.button(pager, 'Anterior', 'chevron-left', () => { this.page--; this.render(); }); back.disabled = this.page === 0;
      pager.createSpan({ text: `${this.page + 1} / ${Math.ceil(entries.length / pageSize)}` });
      const next = p.button(pager, 'Siguiente', 'chevron-right', () => { this.page++; this.render(); }); next.disabled = (this.page + 1) * pageSize >= entries.length;
    }
    const dock = this.contentEl.createDiv({ cls: 'pd-dock', attr: { 'aria-label': 'Barra de tareas y archivos de la carpeta' } });
    p.button(dock, 'Aplicaciones', 'layout-grid', () => p.openApplications());
    const favorites = dock.createDiv('pd-app-favorites');
    for (const id of p.settings.favoriteApps) {
      const app = p.applications.find(item => item.id === id);
      if (!app) continue;
      const button = p.button(favorites, app.name, 'app-window', async () => {
        button.disabled = true;
        try { await p.launchApplication(id); }
        catch (error) { new Notice(error.message, 12000); }
        finally { button.disabled = false; }
      });
      button.title = `Abrir ${app.name}`;
    }
    this.tasksEl = dock.createDiv({ cls: 'pd-tasks', attr: { 'aria-label': 'Ventanas minimizadas', role: 'group' } });
    const launchers = dock.createDiv('pd-launchers');
    for (const file of entries) {
      const b = p.button(launchers, displayName(file), fileIcon(file), () => file instanceof TFolder ? p.openFolder(file.path) : p.openNote(file, this));
      b.dataset.path = file.path; b.title = isPython(file) ? `${file.path} · Abrir en VSCodium` : file.path;
      p.bindFileMenu(b, file, this);
    }
    if (!entries.length) map.createDiv({ cls: 'pd-empty', text: 'Usa Nueva nota o Nueva carpeta para empezar.' });
    p.refreshVisibility();
  }
}

module.exports = class ProjectDesktop extends Plugin {
  async onload() {
    this.settings = Object.assign({ folder: DEFAULT_FOLDER, pinned: false, shortcutFolders: ['Comunidad/Club'], favoriteApps: [] }, await this.loadData());
    if (!Array.isArray(this.settings.favoriteApps)) this.settings.favoriteApps = [];
    this.applications = [];
    try { this.applications = JSON.parse(await this.app.vault.adapter.read(`${this.manifest.dir}/applications.json`)); } catch (_) { /* Catalogue can be refreshed from the launcher. */ }
    if (!Array.isArray(this.applications)) this.applications = [];
    this.desktopModals = new Set();
    this.pending = new Map(); this.panels = new Map(); this.linkHandlers = new WeakSet(); this.destroyed = false;
    this.registerView(TYPE, leaf => new DesktopView(leaf, this));
    this.addCommand({ id: 'open-desktop', name: 'Abrir escritorio del proyecto', callback: () => this.openFolder(this.settings.folder) });
    this.addCommand({ id: 'show-folders', name: 'Mostrar carpetas con vista previa', callback: () => this.showDrawer(true) });
    this.addCommand({ id: 'open-applications', name: 'Buscar y abrir aplicaciones', callback: () => this.openApplications() });
    this.addCommand({ id: 'explore-vault', name: 'Explorar archivos y carpetas de la bóveda', callback: () => this.openExplorer() });
    this.addRibbonIcon('panels-top-left', 'Escritorio de proyectos', () => this.openFolder(this.settings.folder));
    this.registerEvent(this.app.workspace.on('file-menu', (menu, file) => {
      if (file instanceof TFolder) menu.addItem(item => item.setTitle('Abrir como escritorio').setIcon('panels-top-left').onClick(() => this.openFolder(file.path)));
    }));
    for (const event of ['create', 'delete', 'rename', 'modify']) this.registerEvent(this.app.vault.on(event, (file, oldPath) => {
      if (!visible(file)) return;
      if (event === 'rename') {
        for (const [key, panel] of this.panels) if (panel.leaf.view.file === file && key !== file.path) { this.panels.delete(key); this.panels.set(file.path, panel); }
        if (file instanceof TFolder && oldPath) {
          const rebase = path => path === oldPath || path?.startsWith(oldPath + '/') ? file.path + path.slice(oldPath.length) : path;
          this.settings.folder = rebase(this.settings.folder);
          this.settings.shortcutFolders = this.settings.shortcutFolders.map(rebase);
          this.deckPath = rebase(this.deckPath);
          for (const { view } of this.app.workspace.getLeavesOfType(TYPE)) { view.folderPath = rebase(view.folderPath); view.leaf.updateHeader(); }
          for (const [key, panel] of [...this.panels]) {
            panel.project = rebase(panel.project);
            panel.pop.hoverEl.dataset.pdProject = panel.project;
            const path = panel.leaf.view.file?.path;
            if (path && key !== path) { this.panels.delete(key); this.panels.set(path, panel); }
          }
          this.saveData(this.settings);
        }
      }
      if (event === 'delete' && file instanceof TFolder && (this.settings.folder === file.path || this.settings.folder.startsWith(file.path + '/'))) {
        this.openFolder(file.path.split('/').slice(0, -1).join('/'));
      }
      clearTimeout(this.refreshTimer);
      this.refreshTimer = setTimeout(() => { this.renderDrawer(); for (const l of this.app.workspace.getLeavesOfType(TYPE)) l.view.render(); this.updatePanelWallpapers(); }, 300);
    }));
    this.registerEvent(this.app.workspace.on('active-leaf-change', () => this.refreshVisibility()));
    this.registerEvent(this.app.workspace.on('layout-change', () => this.refreshVisibility()));
    this.registerDomEvent(document, 'pointermove', e => {
      if (!this.active || this.settings.pinned) return;
      if (e.clientX <= 12) this.showDrawer(true);
      else if (this.drawerOpen && !this.drawer.contains(e.target) && !this.edge.contains(e.target)) this.scheduleClose();
      else this.cancelClose();
    });
    this.registerDomEvent(window, 'keydown', e => {
      if (e.key === 'Escape' && this.drawerOpen) {
        e.preventDefault();
        e.stopPropagation();
        this.showDrawer(false);
        this.suppressEdgeFocus = true;
        this.edge.focus();
        this.suppressEdgeFocus = false;
      }
    }, { capture: true });
    this.registerDomEvent(window, 'resize', () => this.clampWindows());
    this.buildDrawer();
    document.body.addClass('pd-tabs-bottom');
    this.app.workspace.onLayoutReady(async () => {
      await this.openFolder(this.settings.folder);
      // Reattach windows already open when this plugin is reloaded.
      for (const pop of this.app.plugins.plugins['obsidian-hover-editor']?.activePopovers || []) {
        if (!pop.hoverEl.hasAttribute('data-wallpaper')) continue;
        const leaf = pop.leaves().find(l => l.view.file instanceof TFile);
        if (!leaf) continue;
        const project = pop.hoverEl.dataset.pdProject || leaf.view.file.parent.path;
        const panel = { pop, leaf, project };
        this.panels.set(leaf.view.file.path, panel);
        pop.hoverEl.classList.add('pd-floating');
        this.watchPanel(panel);
      }
      this.updatePanelWallpapers();
    });
  }
  folder(path) { const f = path === '' || path === '/' ? this.app.vault.getRoot() : this.app.vault.getAbstractFileByPath(path); return f instanceof TFolder ? f : null; }
  openDesktopModal(modal) {
    this.showDrawer(false);
    this.desktopModals.add(modal);
    const close = modal.onClose.bind(modal);
    modal.onClose = () => { close(); this.desktopModals.delete(modal); };
    modal.open();
  }
  openApplications() { this.openDesktopModal(new ApplicationsModal(this.app, this)); }
  openExplorer(folder = this.folder(this.currentView?.folderPath || this.settings.folder) || this.app.vault.getRoot()) {
    this.openDesktopModal(new VaultExplorerModal(this.app, this, folder));
  }
  async systemApplications(action, id) {
    if (process.platform !== 'linux') throw new Error('El lanzador de aplicaciones está preparado para Linux.');
    const script = await this.app.vault.adapter.read(`${this.manifest.dir}/applications.py`);
    const flatpak = require('fs').existsSync('/.flatpak-info');
    const args = ['-c', script, action];
    if (id !== undefined) args.push(id);
    return new Promise((resolve, reject) => {
      require('child_process').execFile(flatpak ? 'flatpak-spawn' : 'python3', flatpak ? ['--host', 'python3', ...args] : args,
        { timeout: 20000, maxBuffer: 2 * 1024 * 1024 }, (error, stdout, stderr) => {
          if (error) {
            const permission = flatpak && /portal|denied|not allowed|org\.freedesktop\.Flatpak|serviceunknown/i.test(stderr + error.message);
            reject(new Error(permission ? 'Obsidian necesita autorización para abrir aplicaciones fuera de Flatpak. El permiso del sistema aún no está habilitado.' : 'No se pudo completar la acción: ' + (stderr.trim() || error.message).slice(0, 300)));
            return;
          }
          try { resolve(JSON.parse(stdout)); } catch (_) { reject(new Error('El sistema no devolvió una lista de aplicaciones válida.')); }
        });
    });
  }
  async refreshApplications() {
    const apps = await this.systemApplications('list');
    if (!Array.isArray(apps)) throw new Error('La lista de aplicaciones no es válida.');
    await this.app.vault.adapter.write(`${this.manifest.dir}/applications.json`, JSON.stringify(apps, null, 2));
    this.applications = apps;
    for (const leaf of this.app.workspace.getLeavesOfType(TYPE)) leaf.view.render();
  }
  async launchApplication(id) {
    if (!this.applications.some(app => app.id === id)) throw new Error('La aplicación no está en la lista. Actualiza el catálogo.');
    await this.systemApplications('launch', id);
  }
  wallpaper(folder) {
    for (let current = folder; current; current = current.parent) {
      const file = current.children?.filter(f => f instanceof TFile && WALLPAPER.test(f.name)).sort((a, b) => a.name.localeCompare(b.name))[0];
      if (file) return file;
    }
    return null;
  }
  palette(folder) {
    for (let current = folder; current; current = current.parent) if (PALETTES[current.path]) return PALETTES[current.path];
    return PALETTES[DEFAULT_FOLDER];
  }
  applyTheme(el, folder) {
    if (!el) return;
    const palette = this.palette(folder);
    el.dataset.pdTheme = palette.name;
    el.style.setProperty('--pd-h', palette.hue);
    el.style.setProperty('--pd-s', palette.saturation + '%');
  }
  clearTheme(el) {
    delete el.dataset.pdTheme;
    el.style.removeProperty('--pd-h'); el.style.removeProperty('--pd-s');
  }
  applyWallpaper(el, folder) {
    this.applyTheme(el, folder);
    const f = this.wallpaper(folder);
    const url = f ? this.app.vault.getResourcePath(f) : '';
    el.style.setProperty('--pd-wallpaper', url ? `url(${JSON.stringify(url)})` : 'none');
    el.dataset.wallpaper = f?.path || '';
  }
  button(parent, text, icon, fn) {
    const b = parent.createEl('button', { attr: { type: 'button', 'aria-label': text } });
    if (icon) { const i = b.createSpan(); setIcon(i, icon); }
    b.createSpan({ text }); b.onclick = fn; return b;
  }
  bindFileMenu(element, file, view = this.currentView) {
    const show = event => {
      event.preventDefault(); event.stopPropagation();
      this.showDrawer(false);
      const menu = new Menu();
      const action = (title, icon, callback) => menu.addItem(item => item.setTitle(title).setIcon(icon).onClick(async () => {
        try { await callback(); } catch (err) { new Notice('No se pudo completar la acción: ' + err.message); }
      }));
      action(isPython(file) ? 'Abrir en VSCodium' : 'Abrir', file instanceof TFolder ? 'folder-open' : fileIcon(file), () => file instanceof TFolder ? this.openFolder(file.path) : this.openNote(file, view));
      if (file instanceof TFolder) {
        action('Nueva nota', 'file-plus', async () => { await this.openFolder(file.path); return this.createNote(file); });
        action('Nueva carpeta', 'folder-plus', () => this.createFolder(file));
      }
      menu.addSeparator();
      action('Renombrar…', 'pencil', () => this.app.fileManager.promptForFileRename(file));
      action('Mover a…', 'folder-input', () => new MoveFileModal(this.app, file).open());
      action('Eliminar…', 'trash-2', () => this.app.fileManager.promptForDeletion(file));
      this.app.workspace.trigger('file-menu', menu, file, 'project-desktop');
      if (event.type === 'keydown') {
        const rect = element.getBoundingClientRect();
        menu.showAtPosition({ x: rect.left, y: rect.bottom });
      } else menu.showAtMouseEvent(event);
    };
    element.oncontextmenu = show;
    element.addEventListener('keydown', event => {
      if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) show(event);
    });
  }
  async openFolder(path) {
    const folder = this.folder(path) || this.folder(DEFAULT_FOLDER) || this.app.vault.getRoot();
    this.settings.folder = folder.path; await this.saveData(this.settings);
    let leaf = this.app.workspace.getLeavesOfType(TYPE).find(l => !l.containerEl.closest('.hover-popover'));
    if (!leaf) {
      // Hover Editor routes new tabs into its active popup. Select a main-workspace leaf first.
      let mainLeaf;
      this.app.workspace.iterateLeaves(this.app.workspace.rootSplit, candidate => {
        if (!candidate.containerEl.closest('.hover-popover')) { mainLeaf = candidate; return true; }
      });
      if (mainLeaf) this.app.workspace.setActiveLeaf(mainLeaf, { focus: false });
      leaf = this.app.workspace.getLeaf('tab');
    }
    await leaf.setViewState({ type: TYPE, state: { folder: folder.path }, active: true });
    await this.app.workspace.revealLeaf(leaf);
    this.app.workspace.setActiveLeaf(leaf, { focus: true });
    this.currentView = leaf.view;
    leaf.updateHeader();
    leaf.tabHeaderEl?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    if (!this.settings.pinned) this.showDrawer(false);
    this.renderDrawer(true); this.refreshVisibility(); this.updatePanelWallpapers();
    return leaf;
  }
  refreshVisibility() {
    if (this.destroyed) return;
    const leaf = this.app.workspace.getLeavesOfType(TYPE).find(l => l.view.containerEl.getBoundingClientRect().width > 0);
    const active = !!leaf;
    this.active = active;
    document.body.toggleClass('pd-active', active);
    this.edge?.toggleClass('pd-hidden', !active);
    if (!active) this.showDrawer(false);
    else { this.currentView = leaf.view; if (this.settings.pinned) this.showDrawer(true); }
    if (active) {
      const folder = this.folder(this.currentView.folderPath);
      for (const el of [this.drawer, this.edge, this.currentView.containerEl]) this.applyTheme(el, folder);
    }
    for (const panel of this.panels.values()) if (panel.pop.hoverEl) {
      const sameProject = active && panel.project === this.currentView?.folderPath;
      panel.pop.hoverEl.classList.toggle('pd-panel-hidden', !sameProject);
    }
    this.renderTaskbars();
  }
  renderTaskbars() {
    if (this.destroyed) return;
    for (const [path, panel] of this.panels) {
      if (!panel.pop.hoverEl.isConnected) { this.releasePanel(panel); this.panels.delete(path); }
    }
    for (const { view } of this.app.workspace.getLeavesOfType(TYPE)) {
      if (!view.tasksEl) continue;
      const scroll = view.tasksEl.scrollLeft;
      view.tasksEl.empty();
      const panels = [...new Set(this.panels.values())].filter(panel => panel.project === view.folderPath && panel.pop.hoverEl.classList.contains('is-minimized'));
      view.tasksEl.hidden = !panels.length;
      for (const panel of panels) {
        const file = panel.leaf.view.file;
        const name = file ? displayName(file) : panel.leaf.view.getDisplayText();
        const button = this.button(view.tasksEl, name, 'panel-top', () => {
          panel.pop.hoverEl.classList.remove('pd-panel-hidden');
          if (panel.pop.hoverEl.classList.contains('is-minimized')) panel.pop.toggleMinimized();
          this.app.workspace.setActiveLeaf(panel.leaf, { focus: true });
          panel.leaf.onResize();
        });
        button.classList.add('pd-task');
        button.dataset.path = file?.path || '';
        button.setAttribute('aria-label', `Restaurar ${name}`);
        button.title = `Restaurar ${name}`;
        if (file) this.bindFileMenu(button, file, view);
      }
      view.tasksEl.scrollLeft = scroll;
    }
  }
  watchPanel(panel) {
    panel.pop.hoverEl.dataset.pdProject = panel.project;
    if (panel.originalToggle) return;
    const { pop } = panel;
    panel.originalToggle = pop.toggleMinimized;
    panel.toggle = (...args) => {
      const el = pop.hoverEl;
      const wasMinimized = el.classList.contains('is-minimized');
      if (!wasMinimized) {
        const r = el.getBoundingClientRect();
        if (r.width && r.height) panel.restoreRect = { left: r.x, top: r.y, width: r.width, height: r.height };
      }
      el.classList.remove('pd-minimized');
      const result = panel.originalToggle.apply(pop, args);
      const minimized = el.classList.contains('is-minimized');
      el.classList.toggle('pd-minimized', minimized);
      if (minimized && this.currentView?.leaf) this.app.workspace.setActiveLeaf(this.currentView.leaf, { focus: true });
      if (!minimized) {
        if (panel.restoreRect) for (const [key, value] of Object.entries(panel.restoreRect)) el.style[key] = value + 'px';
        this.clampWindows();
        panel.leaf.onResize();
      }
      this.renderTaskbars();
      return result;
    };
    pop.toggleMinimized = panel.toggle;
    pop.hoverEl.classList.toggle('pd-minimized', pop.hoverEl.classList.contains('is-minimized'));
  }
  releasePanel(panel) {
    if (panel.pop.toggleMinimized === panel.toggle) panel.pop.toggleMinimized = panel.originalToggle;
    panel.pop.hoverEl.classList.remove('pd-minimized');
  }
  buildDrawer() {
    this.edge = document.body.createEl('button', { cls: 'pd-edge pd-hidden', text: 'Carpetas', attr: { 'aria-label': 'Mostrar carpetas con vista previa', 'aria-expanded': 'false', 'aria-controls': 'pd-folder-drawer' } });
    this.edge.onpointerenter = () => this.showDrawer(true);
    this.edge.onfocus = () => { if (!this.suppressEdgeFocus) this.showDrawer(true); };
    this.edge.onclick = () => this.showDrawer(!this.drawerOpen);
    this.drawer = document.body.createEl('aside', { cls: 'pd-drawer', attr: { id: 'pd-folder-drawer', 'aria-label': 'Carpetas y vistas previas', inert: '' } });
    const header = this.drawer.createDiv('pd-drawer-header');
    header.createEl('h2', { text: 'Tus proyectos' });
    this.pinButton = this.button(header, 'Fijar', 'pin', () => { this.settings.pinned = !this.settings.pinned; this.saveData(this.settings); this.updatePin(); this.showDrawer(true); });
    this.button(header, 'Cerrar', 'x', () => { this.settings.pinned = false; this.saveData(this.settings); this.updatePin(); this.showDrawer(false); });
    this.filter = this.drawer.createEl('input', { cls: 'pd-folder-search', attr: { type: 'search', placeholder: 'Buscar una carpeta…', 'aria-label': 'Buscar carpeta' } });
    this.filter.oninput = () => this.renderDrawer();
    this.cards = this.drawer.createDiv({ cls: 'pd-folder-list', attr: { role: 'region', 'aria-roledescription': 'carrusel', 'aria-label': 'Tarjetero vertical de proyectos' } });
    this.registerDomEvent(this.cards, 'wheel', e => {
      if (e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY) || (this.deckFolders?.length || 0) < 2) return;
      e.preventDefault();
      const now = Date.now();
      if (now < (this.deckWheelUntil || 0)) return;
      if (now - (this.deckWheelLast || 0) > 180) this.deckWheelDelta = 0;
      this.deckWheelLast = now;
      this.deckWheelDelta = (this.deckWheelDelta || 0) + e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? this.cards.clientHeight : 1);
      if (Math.abs(this.deckWheelDelta) < 45) return;
      this.moveDeck(Math.sign(this.deckWheelDelta), this.cards.contains(document.activeElement));
      this.deckWheelDelta = 0;
      this.deckWheelUntil = now + 300;
    }, { passive: false });
    this.registerDomEvent(this.cards, 'keydown', e => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault(); this.moveDeck(e.key === 'ArrowDown' ? 1 : -1, true);
      } else if ((e.key === 'Home' || e.key === 'End') && this.deckFolders?.length) {
        e.preventDefault();
        this.deckPath = this.deckFolders[e.key === 'Home' ? 0 : this.deckFolders.length - 1].path;
        this.layoutDeck(true);
      }
    });
    const nav = this.drawer.createDiv('pd-deck-nav');
    this.deckPrev = this.button(nav, 'Anterior', 'chevron-up', () => this.moveDeck(-1));
    this.deckStatus = nav.createSpan({ cls: 'pd-deck-status', attr: { role: 'status', 'aria-live': 'polite', 'aria-atomic': 'true' } });
    this.deckNext = this.button(nav, 'Siguiente', 'chevron-down', () => this.moveDeck(1));
    this.drawer.createEl('small', { cls: 'pd-deck-hint', text: 'Rueda o ↑ ↓ para explorar · Pulsa la portada para abrir' });
    this.drawer.onpointerenter = () => this.cancelClose();
    this.drawer.onpointerleave = () => this.scheduleClose();
    this.updatePin(); this.renderDrawer();
  }
  updatePin() { this.pinButton?.setAttribute('aria-pressed', String(this.settings.pinned)); this.pinButton?.toggleClass('is-active', this.settings.pinned); }
  renderDrawer(followActive = false) {
    if (!this.cards) return;
    this.cards.empty();
    const query = (this.filter.value || '').toLocaleLowerCase('es');
    const shortcuts = (Array.isArray(this.settings.shortcutFolders) ? this.settings.shortcutFolders : []).filter(path => typeof path === 'string').map(path => this.folder(path)).filter(Boolean);
    const folders = [...new Set([...this.app.vault.getRoot().children, ...shortcuts])].filter(f => f instanceof TFolder && f !== this.app.vault.getRoot() && visible(f) && f.path.toLocaleLowerCase('es').includes(query));
    folders.sort((a, b) => this.palette(a).hue - this.palette(b).hue || a.name.localeCompare(b.name, 'es', { numeric: true }) || a.path.localeCompare(b.path, 'es'));
    this.deckFolders = folders;
    // A nested folder belongs to the closest project represented in the drawer.
    const active = folders.filter(f => this.settings.folder === f.path || this.settings.folder.startsWith(f.path + '/')).sort((a, b) => b.path.length - a.path.length)[0];
    if (followActive || !folders.some(f => f.path === this.deckPath)) this.deckPath = active?.path || folders[0]?.path;
    for (const folder of folders) {
      const b = this.cards.createEl('button', { cls: 'pd-folder-card', attr: { 'data-path': folder.path, 'aria-label': `Abrir ${folder.path}`, type: 'button' } });
      this.applyWallpaper(b, folder);
      b.classList.toggle('is-active', folder === active);
      if (folder === active) b.setAttribute('aria-current', 'page');
      b.title = folder.path;
      this.bindFileMenu(b, folder);
      const top = b.createSpan({ cls: 'pd-folder-top', attr: { 'aria-hidden': 'true' } });
      const icon = top.createSpan({ cls: 'pd-folder-icon' });
      setIcon(icon, this.palette(folder).icon || 'folder');
      top.createSpan({ cls: 'pd-folder-label', text: 'PROYECTO' });
      if (folder === active) top.createSpan({ cls: 'pd-folder-current', text: 'En uso' });
      const text = b.createSpan({ cls: 'pd-folder-info' });
      text.createEl('strong', { text: folder.name });
      const footer = text.createSpan({ cls: 'pd-folder-footer', attr: { 'aria-hidden': 'true' } });
      const children = folder.children.filter(visible);
      const notes = children.filter(f => f instanceof TFile && f.extension === 'md').length;
      const subfolders = children.filter(f => f instanceof TFolder).length;
      const counts = [`${notes} ${notes === 1 ? 'nota' : 'notas'}`];
      if (subfolders) counts.push(`${subfolders} ${subfolders === 1 ? 'carpeta' : 'carpetas'}`);
      footer.createSpan({ cls: 'pd-folder-count', text: counts.join(' · ') });
      const open = footer.createSpan({ cls: 'pd-folder-open' });
      open.createSpan({ text: 'Abrir' });
      setIcon(open.createSpan(), 'arrow-up-right');
      b.onclick = () => {
        if (this.deckPath === folder.path) return this.openFolder(folder.path);
        this.deckPath = folder.path;
        this.layoutDeck(true);
      };
    }
    if (!folders.length) this.cards.createEl('p', { text: 'No hay carpetas con ese nombre.' });
    this.layoutDeck();
  }
  moveDeck(direction, focus = false) {
    const folders = this.deckFolders || [];
    if (folders.length < 2) return;
    const index = Math.max(0, folders.findIndex(f => f.path === this.deckPath));
    this.deckPath = folders[(index + direction + folders.length) % folders.length].path;
    this.layoutDeck(focus);
  }
  layoutDeck(focus = false) {
    const folders = this.deckFolders || [];
    const index = folders.findIndex(f => f.path === this.deckPath);
    for (const [i, card] of [...this.cards.querySelectorAll('.pd-folder-card')].entries()) {
      let offset = (i - index + folders.length) % folders.length;
      if (offset > folders.length / 2) offset -= folders.length;
      const depth = Math.abs(offset);
      card.hidden = depth > 2;
      card.classList.toggle('is-front', depth === 0);
      card.classList.toggle('is-before', offset < 0);
      card.style.setProperty('--pd-offset', String(offset));
      card.style.setProperty('--pd-scale', String(1 - Math.min(depth, 2) * .08));
      card.style.zIndex = String(10 - depth);
      card.tabIndex = depth === 0 ? 0 : -1;
      card.setAttribute('aria-hidden', String(depth !== 0));
      card.setAttribute('aria-label', `${depth === 0 ? 'Abrir' : 'Ver tarjeta de'} ${folders[i].path}`);
    }
    if (this.deckStatus) this.deckStatus.textContent = index < 0 ? 'Sin resultados' : `${index + 1} / ${folders.length} · ${folders[index].name}`;
    if (this.deckPrev) this.deckPrev.disabled = folders.length < 2;
    if (this.deckNext) this.deckNext.disabled = folders.length < 2;
    if (focus) this.cards.querySelector('.is-front')?.focus({ preventScroll: true });
  }
  showDrawer(open) {
    if (!this.drawer) return;
    if (open && !this.drawerOpen) this.renderDrawer(true);
    this.cancelClose(); this.drawerOpen = open;
    this.drawer.classList.toggle('is-open', open);
    this.drawer.inert = !open;
    this.edge.setAttribute('aria-expanded', String(open));
  }
  cancelClose() { clearTimeout(this.closeTimer); this.closeTimer = null; }
  scheduleClose() {
    if (this.settings.pinned || this.closeTimer || !this.drawerOpen) return;
    this.closeTimer = setTimeout(() => {
      this.closeTimer = null;
      if (this.drawer.contains(document.activeElement) && document.activeElement.matches('input,textarea')) return;
      if (this.drawer.matches(':hover')) return;
      this.showDrawer(false);
    }, 450);
  }
  createFolder(folder) { new NewFolderModal(this.app, this, folder).open(); }
  async createNote(folder) {
    try {
      let name = 'Nueva nota', n = 1;
      const prefix = !folder.path || folder.path === '/' ? '' : folder.path + '/';
      while (this.app.vault.getAbstractFileByPath(prefix + name + '.md')) name = `Nueva nota ${++n}`;
      const file = await this.app.vault.create(normalizePath(prefix + name + '.md'), `# ${name}\n\n`);
      const leaf = await this.openNote(file, this.currentView);
      leaf?.view.editor?.setCursor({ line: leaf.view.editor.lastLine(), ch: 0 });
      leaf?.view.editor?.focus();
      return leaf;
    } catch (err) { new Notice('No se pudo crear la nota: ' + err.message); }
  }
  async openPythonFile(file) {
    try {
      const path = this.app.vault.adapter.getFullPath(file.path);
      const { pathToFileURL } = require('url');
      const url = 'vscodium://file' + pathToFileURL(path).pathname;
      await require('electron').shell.openExternal(url);
    } catch (err) {
      console.error('[project-desktop] VSCodium', err);
      new Notice('No se pudo abrir el archivo en VSCodium: ' + err.message);
    }
  }
  async openNote(file, view = this.currentView) {
    if (!(file instanceof TFile)) return;
    if (isPython(file)) return this.openPythonFile(file);
    if (this.pending.has(file.path)) return this.pending.get(file.path);
    const promise = this.doOpenNote(file, view).catch(err => { console.error('[project-desktop]', err); new Notice('No se pudo abrir la ventana: ' + err.message); }).finally(() => this.pending.delete(file.path));
    this.pending.set(file.path, promise); return promise;
  }
  async doOpenNote(file, view) {
    const plugin = this.app.plugins.plugins['obsidian-hover-editor'];
    if (!plugin?.spawnPopover) { new Notice('Activa Hover Editor para abrir notas flotantes.'); return; }
    let pop = plugin.activePopovers.find(p => p.leaves().some(l => l.view.file?.path === file.path));
    let leaf = pop?.leaves().find(l => l.view.file?.path === file.path);
    if (!leaf) {
      if (view?.leaf) this.app.workspace.setActiveLeaf(view.leaf, { focus: false });
      let shown;
      const ready = new Promise(resolve => { shown = resolve; });
      leaf = plugin.spawnPopover(view?.containerEl, shown);
      await leaf.openFile(file, file.extension === 'md' ? { state: { mode: 'source' } } : {});
      await ready;
      pop = plugin.activePopovers.find(p => p.leaves().includes(leaf));
    }
    if (!pop) throw new Error('Hover Editor no ha creado su ventana.');
    if (pop.hoverEl.classList.contains('is-minimized')) pop.toggleMinimized();
    pop.togglePin(true);
    pop.hoverEl.classList.add('pd-floating'); pop.hoverEl.classList.remove('pd-panel-hidden');
    const project = view?.folderPath || this.settings.folder;
    const existing = this.panels.has(file.path);
    let panel = [...this.panels.values()].find(p => p.pop === pop);
    if (!panel) panel = { pop, leaf, project };
    else Object.assign(panel, { leaf, project });
    this.panels.set(file.path, panel);
    this.watchPanel(panel);
    this.applyWallpaper(pop.hoverEl, this.wallpaper(file.parent) ? file.parent : this.folder(project));
    if (!existing) {
      const count = [...this.panels.values()].filter(p => p.project === project && p.pop.hoverEl.isConnected).length;
      const w = Math.min(570, Math.max(340, innerWidth * .43));
      const h = Math.min(480, Math.max(300, innerHeight * .6));
      Object.assign(pop.hoverEl.style, { width: w + 'px', height: h + 'px', left: Math.max(24, innerWidth - w - 30 - ((count - 1) % 3) * 25) + 'px', top: Math.min(95 + ((count - 1) % 3) * 75, innerHeight - h - 75) + 'px', transform: 'none' });
    }
    this.clampWindows(); leaf.onResize();
    this.app.workspace.setActiveLeaf(leaf, { focus: true });
    if (leaf.view.getMode?.() === 'source') leaf.view.editor?.focus();
    if (!this.linkHandlers.has(pop.hoverEl)) this.registerDomEvent(pop.hoverEl, 'click', e => {
      const a = e.target.closest?.('a.internal-link');
      if (!a || e.ctrlKey || e.metaKey || e.shiftKey) return;
      const target = this.app.metadataCache.getFirstLinkpathDest(a.dataset.href || a.getAttribute('href'), file.path);
      if (target) { e.preventDefault(); e.stopPropagation(); this.openNote(target, view); }
    }, true);
    this.linkHandlers.add(pop.hoverEl);
    this.renderTaskbars();
    return leaf;
  }
  updatePanelWallpapers() {
    for (const [path, panel] of this.panels) {
      if (!panel.pop.hoverEl.isConnected) { this.releasePanel(panel); this.panels.delete(path); continue; }
      const file = panel.leaf.view.file;
      this.applyWallpaper(panel.pop.hoverEl, this.wallpaper(file?.parent) ? file.parent : this.folder(panel.project));
    }
    this.refreshVisibility();
  }
  clampWindows() {
    for (const { pop, leaf } of this.panels.values()) {
      if (!pop.hoverEl.isConnected || pop.hoverEl.classList.contains('is-minimized') || pop.hoverEl.classList.contains('pd-panel-hidden')) continue;
      const r = pop.hoverEl.getBoundingClientRect();
      const w = Math.min(r.width || 500, innerWidth - 32), h = Math.min(r.height || 400, innerHeight - 110);
      Object.assign(pop.hoverEl.style, { width: w + 'px', height: h + 'px', left: Math.max(16, Math.min(r.x, innerWidth - w - 16)) + 'px', top: Math.max(30, Math.min(r.y, innerHeight - h - 65)) + 'px' });
    }
  }
  onunload() {
    this.destroyed = true; clearTimeout(this.refreshTimer); this.cancelClose();
    for (const modal of this.desktopModals || []) modal.close();
    this.drawer?.remove(); this.edge?.remove();
    document.body.removeClass('pd-tabs-bottom', 'pd-active');
    for (const panel of this.panels.values()) { this.releasePanel(panel); const { pop } = panel; pop.hoverEl.classList.remove('pd-floating', 'pd-panel-hidden'); pop.hoverEl.style.removeProperty('--pd-wallpaper'); this.clearTheme(pop.hoverEl); }
    this.app.workspace.detachLeavesOfType(TYPE);
  }
};
