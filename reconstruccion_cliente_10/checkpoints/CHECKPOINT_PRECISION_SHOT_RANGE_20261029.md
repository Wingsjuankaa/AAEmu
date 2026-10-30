# Disparo de precisión 23592: alcance corregido en caliente

Target rama_10/HEAD9c74824659cc0d144f5e450e3bd7157624e539c3, padre exacto
upstream/client_version/zone-10.0.2_r575@78533663d9ca93dc4aa610c088359312f91f4293.

Detalle y límites: `Docs/AA10PrecisionShotRange_es.md`.

El usuario reprodujo casteo sin daño a30,3 m en el nuevo sandbox411.
Skill23592/plot1226/event9896 usa línea4843 con valores3/25/3; max_range45.
Full, compact principal y dos derivados privados coinciden. El OBB nativo
expresa semiextensiones: ComputeCorridor y su broad phase usaban media
longitud como longitud completa. Corregidos ambos métodos sin excepción por
skill, sin alterar datos, fórmula de daño ni rango de lanzamiento.

NativeZoneSHA8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a;
consumer de volumenRVA0x7b7e60 reanclado byte a byte. Representación nativa
confirmada; no se cierra el selector servidor nativo completo ni calc_distance,
adjust_angle o endpoints independientes del PlotObject. AA8 sólo comparador.

Extractor read-only con654 filas, integridad y dos salidas SQLite idénticas:
SHA8193e9150eb5d3eb24e514d4d1f683b651d775c4c52ef83dd944af73470604e1.
Prueba focal antes:5 fallos/2 éxitos; después7/7. Restore/build Release sin
errores; suite completa8913/8913, sin omitidas. Diff sin errores de whitespace.

Hot Reload real:World396, CLR0→2, Native31564/sesión3225459956 y cliente26548
conservados; Sandbox1001/obj273 conectado. Usuario confirmó daño a30 m y
a44–45 m. Logs confirman WZUnitDamaged23592, últimoTL35/dmg5233.
Native habitual23668 intacto. Imagen Game habitual no recreada: reporte5
requiere repetir con Dannia en ese despliegue. No confundir esta reparación
geométrica con la reconstrucción completa de la habilidad y sus combos.

Evidencia y rollback por dos fuentes anteriores:
`E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/precision-shot-range-20261029`.
Manifiesto de entrega y capturas precision-shot-before,
precision-shot-hot-reload-applied, precision-shot-user-final-accepted.
Sin lifecycle de Zones ni manejo del escritorio; todo nuevo en E.
