# Código y gráficas en las notas

Los colores salen en la **vista de lectura** (botón «Vista previa» o Ctrl+S). En «Editar» se ve el texto tal cual.

## Código

Escribe tres comillas invertidas (en el teclado español, la tecla a la derecha de la P y después espacio) seguidas del lenguaje, el código, y otras tres comillas para cerrar:

```python
def saludo(nombre):
    # Un comentario
    return f"Hola, {nombre}"

print(saludo("PrOSperus"), 42)
```

Así se escribe lo de arriba:

~~~text
```python
def saludo(nombre):
    return f"Hola, {nombre}"
```
~~~

Valen `python`, `java`, `c`, `cpp`, `bash`, `sql`, `rust`, `js`, `matlab`… Sin el nombre del lenguaje, o con uno que no existe, el bloque sale con su fondo y letra de código, pero sin colores.

## Gráficas

```grafica
tipo: barras
titulo: Horas por semana
Semana, Diseño, Pruebas
1, 4, 2
2, 6, 3
3, 3, 5
```

`tipo:` puede ser `barras`, `lineas` o `tarta`.
