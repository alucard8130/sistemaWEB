**GESAC**

Sistema de Gestión Administrativa Condominal

**Manual de Usuario**

*Versión unificada — Agosto 2026*

Para administradores, condóminos y empresas administradoras

**Contenido**

- 1. Introducción y primeros pasos

- 2. Segmentos: Comercial y Habitacional

- 3. Módulo de Propiedades

- 4. Áreas Comunes (segmento Comercial)

- 5. Facturación

- 6. Cobros y Cobros Automáticos con IA

- 7. Gastos

- 8. Caja Chica

- 9. Otros Ingresos

- 10. Traspasos Bancarios

- 11. Módulo de Inversiones

- 12. Saldos por Período y Cierre de Períodos

- 13. Política de Seguridad de Fechas

- 14. Cortes de Estacionamiento

- 15. Control de Ingresos por Sanitarios

- 16. Cartera de Cobranza

- 17. Presupuestos

- 18. Estadísticas, Reportes y Exportaciones

- 19. Catálogo de Cuentas Contables

- 20. Rol de Contador

- 21. Asistente Sherlock

- 22. Control de Asistencia

- 23. Configuración Inicial (carga de datos)

- 24. Portal de Acceso Externo (Administradoras y Comités)

- 25. App Móvil GESAC

- 26. Preguntas Frecuentes

- 27. Contacto y Soporte

# 1. Introducción y primeros pasos

GESAC es un sistema de gestión administrativa diseñado para empresas y personas que administran condominios, plazas comerciales, unidades habitacionales, arrendamientos y propiedades en régimen de cartera. Permite controlar cobranza, facturación fiscal, gastos, presupuestos y reportes financieros desde un solo lugar, con Inteligencia Artificial ayudando en las tareas más pesadas — accesible tanto desde computadora como desde dispositivos móviles.

## 1.1 Requisitos para empezar a usar GESAC

- Tu condominio o propiedad debe estar contratado bajo el servicio GESAC Web.

- Conexión a internet (computadora, tablet o smartphone).

- Para administradores: navegador actualizado (Chrome, Edge o Safari).

- Para condóminos: app GESAC Condóminos (iOS).

> Nota Si tu condominio no aparece al intentar registrarte en la app, solicita a tu administrador que confirme que la propiedad ya está dada de alta en el sistema.

## 1.2 Acceso al sistema web

1. Ingresa a la dirección web proporcionada por tu proveedor de GESAC.

2. Introduce tu usuario y contraseña.

3. Si administras más de un condominio o empresa, selecciona con cuál deseas trabajar.

> Nota Si olvidaste tu contraseña, usa la opción de recuperación en la pantalla de inicio de sesión, o contacta a soporte.

## 1.3 Panel principal (Dashboard)

Al iniciar sesión llegarás al panel principal, donde encontrarás un resumen general de la situación financiera de tu condominio o cartera: ingresos del mes, gastos, cartera vencida, gráficas de tendencia, y accesos directos a los módulos más usados.

# 2. Segmentos: Comercial y Habitacional

GESAC se adapta automáticamente según el tipo de propiedad que administras. Al registrarte, seleccionas tu segmento, y esto determina la terminología y las funciones disponibles en todo el sistema.

  —————————— ———————————— ————————————————-
  **Aspecto**                    **Comercial**                        **Habitacional**

  Propiedades                    Locales comerciales en renta         Viviendas: casas y departamentos

  Áreas comunes                  Generan renta/cuota, con contratos   No aplican — amenidades incluidas en la cuota

  Tipo de cuota "Renta"        Disponible                           No disponible

  Campo "Giro"/"Ubicación"   Visible en el alta de propiedad      Oculto (no aplica a una vivienda)
  —————————— ———————————— ————————————————-

Todo lo demás — facturación, cobros automáticos con IA, cartera vencida, checador de personal, reportes financieros, Sherlock — funciona exactamente igual en ambos segmentos.

> ¿Puedo cambiar de segmento después? El segmento se define al registrar tu condominio. Si necesitas cambiarlo, contacta a tu proveedor de GESAC.

# 3. Módulo de Propiedades

Administra el cobro y la facturación de los locales comerciales o viviendas dentro de tu condominio.

## 3.1 Registrar una propiedad nueva

1. Ve a Propiedades → Nueva Propiedad.

2. Captura el número o identificador (ej. "Local 101" o "Depto-25A").

3. Selecciona o crea el cliente (propietario, inquilino o residente).

4. Elige el tipo de propiedad y captura la cuota mensual.

5. Guarda — el sistema genera automáticamente la primera factura del mes.

> Carga masiva Si tienes muchas propiedades, descarga la plantilla de Excel desde "Carga Masiva" y sube todas de una sola vez. La plantilla para condominios habitacionales ya no incluye las columnas de "Giro" ni "Ubicación".

## 3.2 Registrar cobranza

1. Busca el local o cliente correspondiente.

2. Selecciona "Registrar pago" y captura monto, forma de pago y fecha.

3. Guarda — el saldo de la propiedad se actualiza automáticamente.

## 3.3 Facturación y notas de crédito

- La facturación genera el comprobante fiscal (CFDI) correspondiente al cobro.

- Las notas de crédito se usan para cancelar o ajustar un cobro ya facturado.

> Importante Verifica los datos fiscales del cliente antes de timbrar: una vez generado el CFDI, cualquier corrección requiere una nota de crédito o cancelación ante el SAT.

## 3.4 Reglas automáticas al editar una propiedad

Para que el Estado y el Cliente de cada propiedad nunca queden en una combinación contradictoria, GESAC aplica automáticamente estas reglas al guardar cualquier edición:

- La cuota nunca puede quedar en \$0.00 — si intentas guardar una propiedad sin cuota, el sistema lo bloquea.

- Si seleccionas un cliente nuevo o distinto al que ya tenía, el Estado pasa automáticamente a "Ocupado", sin importar qué opción hayas dejado seleccionada.

- Si cambias el Estado a "Disponible" sin haber asignado un cliente nuevo, el cliente que estuviera asignado se libera automáticamente.

> Ejemplo Editas un local que estaba "Ocupado" por un inquilino que se va. Cambias el Estado a "Disponible" y guardas, sin tener que buscar y quitar manualmente el cliente del selector — GESAC lo libera solo.

# 4. Áreas Comunes (segmento Comercial)

Permite gestionar el cobro por uso de espacios comunes de la plaza o centro comercial, como salones de eventos, canchas o estacionamientos. No aplica al segmento habitacional — ahí las amenidades no generan facturación.

- Alta de área común: registra el espacio y su tarifa.

- Registro de contratos: documenta el acuerdo de uso entre el condominio y quien renta el área.

- Búsqueda y edición de contratos existentes.

- Cobranza y facturación: mismo flujo que en propiedades.

# 5. Facturación

## 5.1 Facturación mensual automática

Genera automáticamente las cuotas mensuales de todas tus propiedades, evitando capturarlas una por una.

1. Ve a Facturación → Generación Mensual de Cuotas.

2. El sistema muestra cuántas propiedades faltan por facturar del periodo más antiguo pendiente.

3. Confirma la generación — el sistema crea las cuotas correspondientes.

> Nota Solo puedes facturar el periodo más antiguo pendiente, uno a la vez — esto evita saltarte meses por error. Ejecuta la facturación masiva en horarios de menor uso, ya que puede tardar varios minutos según el número de propiedades.

## 5.2 Actualización de cuotas

Permite modificar el monto de las cuotas mensuales, por ejemplo ante un ajuste anual por inflación.

- Selecciona el tipo de cartera a actualizar.

- Indica el nuevo monto o el porcentaje de incremento.

- Aplica el cambio — las cuotas futuras usan el nuevo monto; las ya generadas no se modifican retroactivamente.

## 5.3 Tipos de cuota disponibles

- Mantenimiento — la cuota mensual regular.

- Renta — solo en segmento Comercial.

- Depósito en Garantía

- Extraordinaria — para gastos especiales aprobados en asamblea.

- Multa

- Intereses

## 5.4 Grupos de Facturación (varios locales, una sola factura)

Cuando un mismo cliente tiene varios locales o áreas y prefiere recibir UNA sola factura consolidada en vez de una por cada propiedad, puedes agruparlos en un Grupo de Facturación.

1. Ve a Facturación → Grupos de Facturación y crea un grupo nuevo para el cliente.

2. Selecciona qué locales o áreas de ese cliente quedan incluidos en el grupo.

3. A partir del siguiente ciclo de facturación, esas propiedades generan una sola factura con el monto sumado, en vez de facturas separadas.

> En pocas palabras No se desglosa el monto por local dentro de la factura — se muestra el total combinado, con la lista de locales incluidos como referencia. Puedes agregar o quitar locales de un grupo en cualquier momento; el cambio aplica desde el siguiente periodo de facturación.

## 5.5 Pools de Vacancia (cobrar la vacancia a un tercero)

Cuando algunos locales pasan temporadas vacíos entre inquilinos, y tienes un tercero (inversionista, garante, desarrollador) que se compromete a cubrir esa renta mientras estén vacíos, un Pool de Vacancia factura automáticamente esa cobertura cada mes — sin llevar la cuenta a mano de qué está vacío.

1. Ve a Propiedades → Pools de Vacancia → Nuevo pool, y asígnale el cliente que cubre.

2. Marca qué locales son elegibles para este pool — solo se pueden marcar locales con Estado "Disponible".

3. Cada mes, GESAC suma automáticamente la cuota de los locales del pool que sigan en "Disponible", y genera UNA factura consolidada al cliente que cubre.

> El truco está en el Estado del local En cuanto asignas un cliente real a un local del pool (Regla de la sección 3.4), su Estado pasa a "Ocupado" automáticamente — deja de cobrarse al pool y empieza a facturarse a su nuevo inquilino, sin tocar nada en la pantalla del pool. Si ese inquilino se va después, basta con volver a poner el local en "Disponible" (libera el cliente solo) para que regrese al cálculo del pool el siguiente mes.

> Identificarlos en la Lista de Propiedades Un ícono ámbar junto al número del local indica que está vacío y facturándose al pool este mes; un ícono gris indica que pertenece al pool pero está ocupado (no se cobra mientras tanto).

## 5.6 Cuota Anual de Propiedades

Por defecto, las propiedades se facturan cada mes. Activando "¿Cuota anual?" en un local, vivienda o área común, GESAC genera UNA sola factura al año en vez de 12 — útil para acuerdos de pago único anual.

> Regla de oro El campo Cuota de la propiedad SIEMPRE representa el importe MENSUAL, exactamente igual que en una propiedad normal — nunca captures el total anual. GESAC multiplica automáticamente por 12 al generar la factura: cuota mensual \$1,000 → factura anual \$12,000.

- La factura anual se revisa cada vez que corre la facturación (manual o automática), sin importar el mes — no depende de que se ejecute justo en enero.

- Solo se genera una vez por año calendario: si ya existe, GESAC la omite en corridas posteriores del mismo año.

- En la pantalla de Confirmar Facturación aparece un aviso ámbar "Cuotas anuales pendientes" cuando falte alguna, con un botón para generarlas de inmediato, sin depender del backlog mensual.

# 6. Cobros y Cobros Automáticos con IA

## 6.1 Registro manual de cobros

Busca la factura del cliente en Facturas de Cuotas, da clic en "Registrar pago", y captura fecha, monto y cuenta bancaria. Ideal para pagos ocasionales o en efectivo.

## 6.2 Cobros Automáticos por Estado de Cuenta (IA)

Disponible para empresas con plan PREMIUM. Sube el estado de cuenta bancario de tu condominio, y el sistema identifica automáticamente qué depósitos corresponden a qué clientes, usando Inteligencia Artificial.

> En pocas palabras 1\) Subes tu estado de cuenta (Excel o CSV). 2\) El sistema lee los movimientos y sugiere a qué cliente pertenece cada depósito. 3\) Tú revisas cada movimiento y decides: aplicarlo, crear una factura nueva, o ignorarlo.

### 6.2.1 Referencias de pago por propiedad

Cada local comercial y cada área común tiene su propia referencia de pago única, con formato RF-00042-LD02-X7K3 (número de cliente, tipo de propiedad, número, código de seguridad). La referencia siempre pertenece a la PROPIEDAD, nunca al cliente en general — si un cliente tiene varios locales, cada uno conserva su propia referencia independiente.

- Descarga la referencia de una propiedad desde la lista de Locales o Áreas Comunes — incluye datos bancarios y código QR para pago por SPEI.

- Desde la lista de clientes puedes descargar un PDF consolidado con todas las referencias de sus propiedades, cada una en su propia página.

- El PDF de referencia incluye una invitación a pagar también desde la App GESAC Condóminos o el Portal Web, con las URLs en texto listas para teclear si el documento se imprime.

> Importante Una propiedad solo genera su referencia de pago automáticamente cuando ya tiene un cliente asignado. Las cuentas bancarias marcadas como "Inversión" nunca aparecen en el PDF de referencia de pago — solo se muestran las cuentas destinadas realmente a recibir cobros de clientes.

### 6.2.2 Formatos de archivo aceptados

El sistema acepta Excel (.xls, .xlsx) y CSV (.csv). Los archivos PDF no se aceptan directamente en el formulario de carga.

> ¿Tu estado de cuenta es un PDF? Usa la herramienta "Convertir a Excel y descargar" dentro de Cobros Automáticos. Revisa el Excel resultante (fechas, descripciones y montos) antes de subirlo — la conversión es automática y en casos raros puede leer mal alguna columna. El sistema solo acepta estados de cuenta del año en curso.

### 6.2.3 Niveles de confianza en la identificación

  ————— ———————————————————————————————--
  **Nivel**       **¿Qué significa?**

  ALTA            La referencia de pago exacta de una propiedad aparece en el movimiento. Prácticamente seguro.

  MEDIA           El nombre del cliente coincide claramente con la descripción del depósito.

  BAJA            Coincidencia débil — conviene revisarla con cuidado.

  SIN MATCH       No se identificó a ningún cliente. Requiere asignación manual.
  ————— ———————————————————————————————--

### 6.2.4 Acciones disponibles por movimiento

- Asignar a una factura existente — registra el pago y actualiza el estatus de la factura.

- Crear una factura nueva — genera la factura de cuota u otros ingresos con el pago ya aplicado.

- Depósito no identificado — registra el dinero como recibido sin vincularlo a ningún cliente, para investigarlo después.

- Ignorar — si el movimiento no corresponde a un cobro de cliente (traspaso interno, por ejemplo).

> Importante Cada acción es individual: revisas movimiento por movimiento, no hay botón de "aplicar todo". Una vez aplicado un movimiento, queda registrado y ya no puede deshacerse desde esta pantalla.

## 6.3 Saldo a Favor de Clientes (pagos adelantados)

GESAC solo genera la factura del mes que ya llegó — nunca genera facturas futuras por adelantado. Cuando un cliente paga de más (por ejemplo, adelanta varios meses en un solo depósito), ese sobrante se registra como Saldo a Favor, y el sistema lo aplica solo, mes con mes, en cuanto cada factura futura se genera.

1. Registra primero el pago normal contra la factura del mes en curso, como siempre.

2. Ve a Facturación → Saldos a Favor → Registrar nuevo, y captura el cliente, el sobrante, la forma de pago y la fecha.

3. Indica la cuenta bancaria donde cayó el dinero — obligatorio, salvo que la forma de pago sea Efectivo.

4. Opcionalmente, liga el saldo a una propiedad específica del cliente (recomendado si tiene varias).

> Aplicación automática, mes con mes Cada vez que se genera una factura nueva para ese cliente, GESAC revisa si tiene saldo a favor disponible y lo aplica automáticamente, marcando la factura como "Cobrada" si queda cubierta al 100% — hasta agotar el saldo. Si hay varios saldos del mismo cliente, se consume primero el más antiguo (FIFO).

> No lo confundas con Cuota Anual Cuota Anual (sección 5.6) es un interruptor de frecuencia de facturación de una propiedad. Saldo a Favor es dinero de un pago adelantado que espera a que existan facturas mensuales futuras \-- son mecanismos distintos para necesidades distintas.

# 7. Gastos

## 7.1 Registro de gastos

1. Ingresa al módulo Gastos.

2. Captura el concepto, proveedor, monto y fecha del gasto.

3. Guarda el registro.

## 7.2 Proveedores y empleados

- Da de alta proveedores antes de registrar un gasto asociado a ellos (o deja que Sherlock los detecte automáticamente — ver sección 21).

- El catálogo de empleados permite asociar gastos de nómina o pagos a personal del condominio.

## 7.3 Validación de presupuesto al solicitar un gasto

Al crear la solicitud, GESAC compara automáticamente la cuenta de gasto contra su presupuesto capturado y disponible para ese año — ver el detalle completo de esta política en la sección 17, Presupuestos.

> En una frase Si la cuenta no tiene presupuesto capturado, o el monto excede lo disponible, GESAC te avisa con el desglose completo — pero la solicitud se guarda de todas formas.

## 7.4 Lista de solicitudes de gasto — filtros y KPIs

- Filtro por Estatus: Todos / Pendiente / Pagada / Cancelada.

- Filtro por Fecha inicio y Fecha fin (los filtros se mantienen al paginar).

- KPIs del período: total de solicitudes, número y monto pagado/pendiente con porcentaje, total solicitado.

> Nota Por defecto se muestra el período de enero al día de hoy. Si aplicas filtros de fecha, los KPIs se adaptan automáticamente.

## 7.5 Reporte de gastos

Genera un reporte por periodo con el desglose de todos los gastos registrados, exportable a PDF o Excel.

# 8. Caja Chica

Controla el efectivo destinado a gastos menores del día a día.

- Fondeos de caja chica: registra el cheque o efectivo entregado a un responsable, ligado a una cuenta bancaria de origen.

- Vales de caja chica: documenta un anticipo entregado con cargo al fondeo.

- Gastos de caja chica: documenta en qué se utilizó el efectivo entregado, con su comprobante.

> Nota Concilia la caja chica periódicamente para evitar diferencias acumuladas entre el efectivo entregado y el comprobado. Un fondeo solo se puede eliminar si nunca se le ha registrado ningún vale o gasto — es decir, si su saldo sigue igual al importe original del cheque.

# 9. Otros Ingresos

Registra ingresos que no provienen de cuotas regulares, como rentas eventuales, donativos o ingresos por publicidad.

- Registro de otros ingresos: captura el concepto y el monto recibido.

- Reporte de ingresos: muestra el total del periodo, incluyendo cuotas y otros ingresos.

# 10. Traspasos Bancarios

Permite registrar movimientos de dinero entre cuentas bancarias de la misma empresa, manteniendo un registro histórico y actualizando automáticamente los saldos.

## 10.1 Registrar un traspaso

1. Haz clic en "Nuevo traspaso".

2. Selecciona la cuenta origen y la cuenta destino — el sistema muestra el saldo disponible de cada una.

3. Ingresa el monto, fecha, referencia y concepto.

4. El sistema verifica que haya saldo suficiente en la cuenta origen y guarda, actualizando ambos saldos.

## 10.2 Cancelar un traspaso

En la lista de traspasos, da clic en "Cancelar" y confirma — los saldos de ambas cuentas se revierten automáticamente.

> Importante Solo se pueden cancelar traspasos con estado "Completado". Los traspasos ya cancelados no se pueden reactivar.

# 11. Módulo de Inversiones

Permite administrar el dinero que tu condominio mantiene en cuentas de inversión (pagarés, fondos, o cualquier instrumento que genere rendimientos), llevando un control separado de aportaciones, rendimientos, retenciones de impuestos y retiros — con reportes comparativos igual que el resto de tus cuentas bancarias.

> En pocas palabras Tu cuenta de inversión es una Cuenta Bancaria más (tipo "Inversión"). Los movimientos se registran con 4 tipos distintos, cada uno con su propio efecto contable, y el reporte te muestra cómo ha crecido tu inversión mes a mes y año contra año.

## 11.1 Configurar tu cuenta de inversión

Antes de registrar movimientos, da de alta una cuenta bancaria del tipo "Inversión" (Catálogos → Cuentas Bancarias → Nueva Cuenta), igual que cualquier otra cuenta de tu empresa.

## 11.2 Tipos de movimiento

  ———————- —————————————————————————————————————————————--
  **Tipo**               **¿Qué hace?**

  Incremento             Traspasa dinero de una cuenta normal hacia tu cuenta de inversión. El sistema valida que la cuenta de origen tenga saldo suficiente.

  Rendimiento            Registra el interés que generó tu inversión, como un Otro Ingreso que crece dentro de la misma cuenta — no requiere cuenta de origen.

  Retención de ISR       Registra el impuesto retenido sobre el rendimiento, como un Gasto independiente — no afecta el saldo bancario de ninguna cuenta.

  Retiro / Liquidación   Traspasa dinero de tu cuenta de inversión de vuelta a una cuenta normal. Valida que la inversión tenga saldo suficiente.
  ———————- —————————————————————————————————————————————--

## 11.3 Registrar un movimiento

1. Ve a Ingresos → Reporte Inversiones → Registrar movimiento de inversión.

2. Selecciona el tipo: Incremento, Retiro, o Registrar Retención de ISR (esta última tiene su propia pantalla, separada).

3. Para Incremento/Retiro, indica la cuenta de contraparte, el monto y la fecha.

4. Guarda — el sistema actualiza automáticamente los saldos de ambas cuentas involucradas.

> ¿Cómo registro un rendimiento? El rendimiento no se registra desde la pantalla de "Nuevo movimiento" con contraparte — selecciona la opción "Rendimiento", y el sistema te pedirá solo el monto y la fecha, ya que el dinero crece directamente dentro de la cuenta de inversión.

## 11.4 Reporte de Inversión

Disponible en Ingresos → Reporte Inversiones. Muestra, por cada cuenta de inversión:

- Saldo actual, total de incrementos, rendimiento acumulado, y total de retiros.

- Variación del saldo vs. el mes anterior y vs. el mismo periodo del año anterior.

- Rendimiento del mes actual comparado contra el mes anterior, y acumulado del año (YTD) contra el año anterior.

- Historial de los últimos movimientos, con su tipo y fecha.

## 11.5 Cancelar un movimiento

Desde el reporte, los movimientos de Incremento y Retiro tienen un botón para cancelarlos — esto revierte el saldo de ambas cuentas involucradas automáticamente. Los movimientos de Rendimiento no se pueden cancelar desde aquí, ya que ya generaron una factura de Otro Ingreso.

> Importante Cancelar un movimiento no lo borra — lo marca como cancelado para conservar el rastro, y deja de contar en los cálculos de saldo.

## 11.6 Reiniciar saldos por período (solo administrador)

Si tus saldos por período dejan de cuadrar (por ejemplo, después de corregir movimientos históricos), existe una herramienta para reiniciar el caché de cálculo sin perder tus movimientos reales (pagos, gastos, traspasos).

- Accede desde Conciliaciones → Reiniciar saldos.

- Puedes volver a capturar el saldo inicial de cada cuenta.

> Protegido por contraseña Esta función requiere la contraseña de la cuenta superusuario del sistema, sin importar con qué cuenta esté conectado quien la use — es una acción delicada que borra el caché de saldos históricos, así que está restringida intencionalmente.

# 12. Saldos por Período y Cierre de Períodos

Permite consultar el saldo de cada cuenta bancaria mes a mes, con desglose de ingresos y egresos, y realizar el cierre de períodos para conciliación bancaria.

## 12.1 Detalle de movimientos incluidos

  ————————————-- ——————————--
  **Tipo de movimiento**                 **Afectación**

  Pagos de cuotas                        Ingreso (+)

  Cobros otros ingresos                  Ingreso (+)

  Traspasos recibidos                    Ingreso (+)

  Pagos de gastos                        Egreso (−)

  Fondeos de caja chica                  Egreso (−)

  Traspasos enviados                     Egreso (−)
  ————————————-- ——————————--

## 12.2 Cerrar un período

1. Haz clic en "Cerrar período con saldo del banco".

2. Ingresa el saldo final que aparece en tu estado de cuenta bancario.

3. El sistema muestra la diferencia entre el saldo calculado y el del banco; agrega notas si es necesario.

4. Confirma — el período queda cerrado y el saldo final congelado.

> Importante Una vez cerrado un período, NO se pueden registrar movimientos con fecha dentro de ese período.

# 13. Política de Seguridad de Fechas

GESAC implementa una política de seguridad que protege la integridad de los registros financieros en todos los módulos que afectan saldos bancarios.

## 13.1 Reglas de validación

- No se pueden registrar movimientos con fecha de años anteriores al año actual.

- No se pueden registrar movimientos con fecha futura (posterior a hoy).

- No se pueden registrar movimientos en períodos ya cerrados.

## 13.2 Módulos donde aplica

- Pagos de cuotas, cobros de otros ingresos, pagos de gastos

- Fondeos y gastos de caja chica, vales de caja

- Depósitos por identificar

- Cortes de estacionamiento

- Corte diario de Sanitarios

- Cobros por estado de cuenta bancario (IA)

> Nota Si intentas registrar un movimiento con fecha inválida, el sistema mostrará un mensaje explicando el motivo del bloqueo.

# 14. Cortes de Estacionamiento

Permite registrar los ingresos del estacionamiento bajo dos modalidades de operación distintas, y generar la factura correspondiente. Disponible para empresas con membresía PREMIUM.

> Las dos modalidades Plaza propia: tú controlas el estacionamiento directamente, cobrando por tiempo. El ingreso es el 100% de lo cobrado (efectivo + tarjeta). Operador externo: le das el estacionamiento en operación a un tercero, quien te paga una renta fija mensual. El ingreso para tu plaza ES esa renta completa — no se descuenta nada, y no necesitas (ni puedes) conocer cuánto cobra el operador a los usuarios.

## 14.1 Registrar un nuevo corte

1. Selecciona el tipo de período: semanal, quincenal o mensual, y las fechas de inicio y fin.

2. Si es plaza propia: captura el total en efectivo, total en tarjeta y número de boletos — o mejor, impórtalos automáticamente desde un archivo CSV (ver 14.2).

3. Si es operador externo: activa la casilla correspondiente, captura el nombre del operador y el monto de la renta fija mensual.

4. Guarda el corte.

> El depósito no se captura aquí El corte solo registra los totales del periodo. La cuenta bancaria y la fecha real del depósito se registran después, desde la Lista de Facturas de Otros Ingresos, una vez que el dinero efectivamente se deposite — igual que cualquier otro ingreso del sistema.

## 14.2 Importar tickets desde CSV (solo plaza propia)

En vez de capturar los totales a mano, puedes importar el archivo que exporta el sistema del estacionamiento. El CSV debe tener las columnas: numero_ticket, fecha, hora_entrada, hora_salida, minutos, monto, forma_pago (fecha en formato AAAA-MM-DD, horas en formato HH:MM).

1. Dentro del detalle de un corte, da clic en "Importar tickets CSV".

2. Selecciona el archivo y da clic en "Importar".

3. El sistema crea los tickets y recalcula automáticamente los totales del corte.

> Seguro contra duplicados Si importas el mismo archivo dos veces, el sistema detecta los tickets que ya existen por su número y los omite — nunca duplica un ticket ni infla el total del corte.

## 14.3 Generar la factura del corte

1. Desde la lista de cortes, da clic en el ícono de factura (solo disponible si el corte aún no tiene una).

2. Selecciona el cliente y confirma la fecha de vencimiento.

3. Da clic en "Generar factura" — el monto es siempre el ingreso neto de la plaza (renta completa, o 100% de lo cobrado).

La factura nace "pendiente" — el cobro (con su cuenta y fecha real de depósito) se registra después desde la Lista de Facturas de Otros Ingresos.

> Importante Una vez generada la factura, el corte queda protegido: ya no se puede editar ni eliminar. Si necesitas corregir algo, se ajusta directamente la factura desde el módulo de Otros Ingresos.

# 15. Control de Ingresos por Sanitarios

Permite llevar un registro confiable de tres ingresos en efectivo del día a día: el uso de sanitarios, la venta de papel higiénico, y la venta de toallas sanitarias — con operación desde un link único por caseta, sin que el personal necesite cuenta GESAC.

> Roles bien diferenciados Empleado de caseta: genera, cobra, vende, y cierra su propio corte al terminar su turno. No necesita cuenta GESAC — solo el link de su caseta. Administrador GESAC: configura precios y casetas, consulta el historial de cortes, imprime la carta, recibe el efectivo físico, y registra el depósito. Nunca cobra directamente.

## 15.1 Configuración inicial

1. Ve a Sanitarios → Configurar Sanitarios y captura el precio de Sanitario, Papel y/o Toallas (deja vacío el que no aplique).

2. Marca "boletos físicos" para Sanitario y/o Papel si tu condominio ya reparte boletos pre-numerados en vez de usar códigos virtuales.

3. Ve a Sanitarios → Casetas y crea una caseta por cada punto físico — cada una genera un link único para su tablet o dispositivo.

> Nota Cada administrador ya puede configurar sus propios precios y casetas directamente, sin depender del equipo GESAC para cada ajuste anual de tarifas.

## 15.2 Gafetes de Acceso Gratuito

Empleados de ciertos locales tienen acceso gratuito, identificándose con un gafete físico validado contra un catálogo — el operador nunca puede aceptar un número que no esté dado de alta.

- Registra el gafete con el nombre del titular y el local o área a la que pertenece (ambos obligatorios); el número se genera automáticamente.

- Cada gafete se puede imprimir como credencial física con código QR.

## 15.3 Operación diaria en la caseta

El empleado abre el link de su caseta y ve pestañas para Sanitario, Papel, Toallas, e Historial del día.

- Generar: entrega el siguiente boleto físico, o genera un código virtual, con respuesta instantánea.

- Cobrar: escribe el código al momento de cobrar — se muestran también los pendientes de días anteriores, para nunca perder un cobro atrasado.

- Gratis con gafete: registra el acceso gratuito validado contra el catálogo.

- Toallas: un solo botón "Vender toalla", que descuenta automáticamente del inventario del lote más antiguo disponible.

## 15.4 Cierre de corte — por turno, no por día

Cada corte cubre exactamente el periodo desde el último corte cerrado de esa misma caseta, hasta el momento en que se cierra el nuevo — sin importar si cruza la medianoche.

1. Al final de su turno, el empleado selecciona su nombre de la lista de empleados registrados en GESAC.

2. Da clic en "Cerrar mi corte" — el sistema suma automáticamente todo lo cobrado (de los 3 conceptos) desde el corte anterior.

> Por qué nunca se pierde dinero Como el corte captura por ventana de tiempo (no por fecha calendario), cualquier cobro que ocurra después de un cierre queda automáticamente incluido en el siguiente corte de esa misma caseta.

## 15.5 Historial de Cortes (administrador)

El administrador consulta el historial completo, con filtros por caseta, empleado responsable, o rango de fechas — cada corte muestra el periodo cubierto, quién lo cerró, el total, y si ya se depositó o sigue pendiente.

## 15.6 Ciclo completo del efectivo

1. El empleado cierra su corte al terminar su turno.

2. El administrador imprime la carta de ese corte.

3. El empleado entrega el efectivo físico; ambos firman la carta impresa.

4. El administrador deposita el efectivo al banco.

5. Con la ficha de depósito en mano, el administrador va a Registrar Depósitos, indica la cuenta y la fecha real.

6. El ciclo se cierra: el ingreso queda marcado como cobrado, reflejado en el saldo bancario real.

> Qué sí y qué no resuelve este control El sistema da trazabilidad completa: cada código, boleto o venta queda registrado con fecha, hora, y quién lo generó/cobró. No puede impedir físicamente que un operador deje pasar a alguien sin generar ningún registro — eso requiere control complementario (cámaras, supervisión, auditorías sorpresa).

# 16. Cartera de Cobranza

Visualiza el total de adeudos pendientes, separados por origen. Incluye comparativas mes a mes y año contra año, top de clientes deudores, y gráfica de tendencia — útil para identificar morosidad y priorizar la gestión de cobranza.

# 17. Presupuestos

Construye y registra el presupuesto anual de gastos en una matriz mensual, y GESAC lo usa automáticamente para validar cada solicitud de gasto nueva antes de permitir que se cree — evitando comprometer dinero que no está presupuestado.

## 17.1 Capturar el presupuesto — Matriz mensual

1. Ve a Presupuestos → Matriz Ppto Gastos.

2. Selecciona el año a presupuestar.

3. La matriz muestra cada Grupo, Subgrupo y Tipo de Gasto en filas, con una columna por cada uno de los 12 meses.

4. Captura el monto presupuestado de cada Tipo de Gasto, mes por mes.

5. Guarda — los totales por subgrupo y grupo se calculan automáticamente.

> El presupuesto se captura por Tipo de Gasto específico Cada cuenta de gasto (Tipo de Gasto) necesita su propio presupuesto capturado — no basta con presupuestar a nivel de Grupo o Subgrupo en general.

## 17.2 Cómo se calcula el presupuesto disponible

Aunque se captura mes por mes, la disponibilidad se evalúa siempre de forma ACUMULADA ANUAL — sumando los 12 meses juntos. Puedes usar el presupuesto de cualquier mes del año en el momento que lo necesites, no está encerrado mes a mes.

Lo que cuenta como "ya usado" de ese presupuesto:

- Todo lo que ya se PAGÓ ese año en esa cuenta de gasto.

- Todo lo que sigue PENDIENTE de pago ese año en esa misma cuenta (solicitudes ya creadas, aunque todavía no se hayan pagado).

> Fórmula Presupuesto disponible = Presupuesto anual capturado − (Pagado en el año + Pendiente en el año)

## 17.3 Validación automática al solicitar un gasto

Cada vez que alguien crea una nueva solicitud de gasto, GESAC valida el presupuesto disponible de esa cuenta. La validación es informativa, no bloquea la solicitud — el sistema siempre avisa, pero deja que la solicitud se guarde de todas formas.

> Cambio de política Antes, una solicitud sin presupuesto suficiente se rechazaba por completo. Ahora se guarda igual — GESAC solo te avisa con el mismo detalle de siempre, para que decidas si continuar o ajustarla.

**Caso 1 — La cuenta de gasto no tiene presupuesto capturado**

Si nadie ha capturado presupuesto para esa cuenta ese año, el sistema muestra una advertencia sugiriendo capturar el presupuesto correspondiente en la Matriz — pero la solicitud se guarda de todas formas.

**Caso 2 — El monto solicitado excede lo disponible**

Si el presupuesto existe pero ya está agotado (o casi) por lo pagado y lo pendiente, y la nueva solicitud lo rebasaría, el sistema muestra el desglose completo como advertencia — presupuesto total, cuánto ya está comprometido, cuánto queda disponible, y cuánto se está pidiendo — y la solicitud igual se guarda.

> Qué hacer cuando ves esta advertencia Lee el mensaje — indica exactamente los montos involucrados, para decidir con información completa. Si la cuenta no tiene presupuesto capturado, considera pedirle al administrador que lo capture en la Matriz para que futuras solicitudes se comparen contra un presupuesto real. Si el presupuesto ya se agotó, evalúa si conviene ajustar el monto, esperar al siguiente periodo, o solicitar un ajuste de presupuesto — pero la solicitud ya quedó registrada mientras tanto.

## 17.4 Cierre y reapertura del presupuesto del año

Una vez que el presupuesto de un año queda definido, puedes cerrarlo para evitar modificaciones accidentales durante el resto del ejercicio.

- Cerrar: desde la Matriz, botón "Cerrar presupuesto" — a partir de ese momento, un usuario normal ya no puede editar los montos capturados de ese año.

- Reabrir: solo el superusuario del sistema puede reabrir un presupuesto ya cerrado, autenticándose con su usuario y contraseña directamente en la pantalla de la Matriz.

> Nota Aunque el presupuesto esté cerrado, la validación de solicitudes de gasto sigue funcionando con normalidad — el cierre solo protege la CAPTURA de los montos, no el uso diario del presupuesto ya definido.

## 17.5 Comparativo Presupuesto vs. Real

Disponible en Reportes → Comparativo Ppto vs Gastos. Compara, mes a mes o acumulado, lo presupuestado contra lo realmente ejercido — útil para detectar desviaciones a tiempo y para tus notas a los estados financieros.

# 18. Estadísticas, Reportes y Exportaciones

## 18.1 Dashboards disponibles

- Adeudos de propiedades y áreas comunes

- Ingresos totales

- Gastos y estado de resultados

- Ingresos vs. gastos

- Comparativa de presupuesto contra resultados reales

## 18.2 Exportar Estado de Cuenta a Excel

1. Ve a Facturación → Estado de Cuenta.

2. Selecciona el local o área común y aplica tus filtros.

3. Haz clic en el botón verde "Adeudos" para descargar el Excel.

El archivo incluye folio, cliente, propiedad, tipo de cuota, período, importe, saldo pendiente y observaciones, con el total de adeudo al final.

> Nota El botón solo está activo cuando hay una propiedad seleccionada. Solo exporta facturas pendientes con saldo mayor a cero.

# 19. Catálogo de Cuentas Contables

Permite cargar el catálogo de cuentas contables real de tu condominio (el que usa tu contador), y homologarlo con tus catálogos de GESAC: Tipos de Gasto, Tipos de Cuota, Tipos de Otro Ingreso, y Cuentas Bancarias.

> En pocas palabras 1\) Cargas tu catálogo de cuentas contables (con jerarquía: cuenta mayor y subcuentas). 2\) Homologas tus catálogos de GESAC a esas cuentas. 3\) Exportas la póliza de Gastos o de Ingresos, ya balanceada en partida doble.

## 19.1 Cargar tu catálogo

Columnas del archivo: codigo, nombre_cuenta, codigo_padre, naturaleza (deudora/acreedora), grupo_gasto/subgrupo_gasto, y uso_especial (para homologar cuotas u otros ingresos automáticamente).

1. Entra a Catálogos → Cuentas Contables → Cargar Catálogo.

2. Sube el archivo — el sistema detecta cuentas similares a tus tipos de gasto existentes y te pide confirmar antes de aplicar.

## 19.2 Dónde homologar cada catálogo

  ——————- ————————————-- ——————————————
  **Catálogo**        **Dónde**                              **Notas**

  Tipos de Gasto      Catálogos → Homologar Tipos de Gasto   También automático al cargar el catálogo

  Tipos de Cuota      Catálogos → Homologar Tipos de Cuota   Varios tipos pueden compartir cuenta

  Otros Ingresos      Catálogos → Homologar Otros Ingresos   Un tipo por cuenta contable

  Cuentas Bancarias   Editar la cuenta bancaria              Opcional
  ——————- ————————————-- ——————————————

Ninguna homologación es obligatoria para el uso diario de GESAC — solo es necesaria cuando quieras exportar las pólizas contables.

## 19.3 Exportar pólizas contables

- Póliza de Gastos: Cargo a la cuenta del gasto, Abono a la cuenta bancaria de donde salió el pago.

- Póliza de Ingresos: Cargo a la cuenta bancaria donde entró el dinero, Abono a la cuenta de la cuota u otro ingreso.

> Hoja "Sin homologar" Cualquier movimiento sin homologación completa aparece en una segunda hoja del Excel, indicando exactamente qué le falta.

# 20. Rol de Contador

El rol de Contador es un tipo de acceso especial dentro de GESAC, pensado para el despacho contable o contador externo que lleva la contabilidad de uno o varios condominios. A diferencia de un usuario administrador normal, el Contador ve únicamente un panel reducido con las herramientas contables y financieras que necesita — sin acceso a funciones operativas como cobros, gastos del día a día, propiedades, o comunicación con condóminos.

> En pocas palabras El Contador entra al mismo sistema GESAC, con su propio usuario y contraseña, pero ve un menú distinto y mucho más simple, enfocado en: catálogo contable, pólizas, reportes financieros, presupuestos y nómina. Un mismo Contador puede tener acceso a varios condominios distintos, y cambiar entre ellos desde su propio menú.

## 20.1 Cómo solicitar tu acceso

El Contador no se registra por sí mismo. El acceso lo otorga directamente el administrador del sistema GESAC, a solicitud del condominio o del despacho contable.

1. Contacta al administrador de tu condominio y pídele que solicite tu alta como Contador en GESAC.

2. El administrador se pondrá en contacto con el equipo de GESAC para darte de alta, indicando a qué condominio(s) necesitas acceso.

3. Recibirás un correo directamente de GESAC con tu usuario y una contraseña temporal.

4. La primera vez que inicies sesión, el sistema te pedirá crear tu propia contraseña nueva antes de continuar.

## 20.2 Tu panel principal

Al iniciar sesión llegas directo a tu Panel del Contador — con un menú organizado en 3 grupos: Catálogo Contable, Pólizas y Reportes, y Presupuestos y Nómina.

- Cuentas Contables y Homologación: mismo flujo descrito en la sección 19.

- Póliza de Gastos y de Ingresos, Estado de Resultados, Reporte de Pagos y Otros Ingresos, Cartera Vencida.

- Presupuesto vs. Real (sección 17), Reporte de Asistencia, Incidencias de empleados.

> Si tienes acceso a más de un condominio Verás un selector en tu menú con el condominio activo — recuerda confirmar cuál está seleccionado antes de exportar cualquier reporte.

# 21. Asistente Sherlock

Sherlock es el asistente inteligente de GESAC. Lo encuentras como un ícono flotante con forma de robot en la esquina inferior de cualquier pantalla. Al darle clic, se abre un chat donde puedes pedirle tareas en lenguaje natural, como si le escribieras a una persona.

## 21.1 Acceso según tu plan

  —————- ——————————————————————————————-
  **Plan**         **Acceso a Sherlock**

  Demo             Sin acceso. Se muestra un botón para actualizar tu plan.

  Plus             Alta de clientes, proveedores y empleados.

  Premium          Todo lo de Plus, más: cuentas bancarias, cuentas de gastos, y búsqueda/cobro de facturas.
  —————- ——————————————————————————————-

> Nota Si pides algo que tu plan no incluye, Sherlock te lo dirá y te ofrecerá un botón para actualizar tu membresía sin salir del chat.

## 21.2 Dar de alta un cliente, proveedor o empleado

- Escribe algo como "quiero dar de alta un cliente" (o usa el botón del menú inicial).

- Sherlock pregunta los datos uno por uno; los opcionales puedes saltarlos con un botón.

- Para campos con opciones fijas (régimen fiscal, tipo de cuenta), Sherlock muestra botones en vez de pedirte escribir.

> Nota Sherlock corrige automáticamente el formato: nombres en mayúsculas, correos en minúsculas, RFC en mayúsculas.

## 21.3 Alta de cliente por Constancia Fiscal

En vez de capturar manualmente el RFC, régimen fiscal, código postal y domicilio, sube la Constancia de Situación Fiscal del cliente (PDF, PNG o JPG) y Sherlock extrae los datos automáticamente.

- Si el cliente NO existe: Sherlock crea el registro nuevo con los datos extraídos.

- Si YA existe (mismo RFC): Sherlock muestra qué datos cambiarían y actualiza al confirmar.

> Importante — los datos de la constancia siempre tienen prioridad A diferencia de otras funciones, aquí los datos fiscales SIEMPRE se sobrescriben con lo que traiga la constancia, ya que se usan para timbrar facturas y deben reflejar lo más reciente del SAT.

## 21.4 Auto-alta de proveedores en gastos

Al subir el comprobante de un gasto, ya no es necesario elegir manualmente el proveedor si el comprobante trae su RFC.

- Si el proveedor ya existe (mismo RFC), Sherlock lo asigna automáticamente.

- Si el nombre cambió, Sherlock lo actualiza.

- Si no existe, Sherlock lo crea con el nombre y RFC del comprobante.

## 21.5 Cuentas bancarias y cuentas de gastos (Premium)

Pide "quiero dar de alta una cuenta bancaria" o "una cuenta de gastos", y Sherlock te guía paso a paso — para la cuenta bancaria valida que la CLABE sea correcta antes de aceptarla.

## 21.6 Buscar una factura y asignar un cobro (Premium)

- Escribe algo como "busca la factura del local 12" (también funciona con área común o nombre de cliente).

- Sherlock muestra folio, monto, fecha de vencimiento y estatus.

- Si está pendiente, aparece "Asignar cobro" con el folio precargado — solo falta monto, forma de cobro y opcionalmente fecha y cuenta.

## 21.7 Cancelar una tarea / Actualizar membresía

Da clic en "❌ Cancelar" junto al recuadro de texto para detener una tarea sin guardar nada a medias. Cuando Sherlock te ofrezca actualizar tu plan, el botón dorado abre la página de pago de Stripe — tu membresía se activa automáticamente al confirmarse el pago.

# 22. Control de Asistencia

Permite llevar el registro de entrada y salida de tus empleados desde su propio celular, validando que estén cerca de la ubicación de tu oficina — sin checador físico ni aplicación que instalar.

## 22.1 Configuración inicial (una sola vez, por un administrador)

- Captura la latitud y longitud de tu oficina o caseta (clic derecho sobre el punto en Google Maps para copiar las coordenadas).

- Define el radio permitido en metros.

> Verifica este valor con tu proveedor La documentación fuente reporta valores distintos como radio por defecto (10 m en una versión, 150 m en otra). Confirma cuál es el valor real configurado actualmente en tu sistema.

- En cada empleado, configura (opcional): Hora de entrada esperada, Hora de salida esperada, Tolerancia de retardo en minutos.

> Nota Estos campos son opcionales. Sin ellos, el empleado puede seguir marcando asistencia con normalidad, solo que el sistema no detecta retardos automáticamente.

## 22.2 Compartir el link de asistencia

Cada empleado tiene un link único y permanente. En la lista de empleados, columna "Asistencia", da clic en el ícono verde de WhatsApp — se abre con un mensaje ya redactado, solo confirma el envío.

> Importante Este link identifica al empleado — solo debe compartirse con él. Si deja de trabajar contigo o el link se comparte por error, contacta a soporte para generar uno nuevo.

## 22.3 Cómo marca su asistencia un empleado

1. Abre el link desde su celular (puede guardarlo como acceso directo).

2. Acepta el permiso de ubicación del navegador.

3. Da clic en "Marcar entrada" — si está fuera del rango permitido, se le advierte pero el registro se guarda para revisión.

4. Al final del turno, abre el mismo link, que ahora muestra "Marcar salida".

> Nota No se puede marcar entrada dos veces el mismo día, ni marcar salida sin haber marcado entrada primero.

## 22.4 Reporte de asistencia

- Por defecto muestra el mes en curso; puedes cambiar el rango o filtrar por departamento.

- La tabla muestra, por empleado: días asistidos, retardos, faltas, y porcentaje de asistencia.

- Da clic en un empleado para ver su detalle día por día, incluyendo si cada checada quedó dentro o fuera del rango permitido.

- "Exportar a Excel" descarga el reporte del periodo — pensado para tu proceso de nómina.

> Nota GESAC no procesa nómina — este reporte es informativo, para usarlo como base en el sistema de nómina que ya utilices.

## 22.5 Retardos y faltas automáticos

Retardos: se registran automáticamente cuando la entrada supera la hora esperada más la tolerancia configurada.

Faltas: se detectan bajo demanda. Filtra el rango de fechas, da clic en "Detectar faltas del periodo", y el sistema registra una falta para cualquier empleado sin entrada marcada ese día — a menos que ya tenga una incidencia (permiso, vacaciones, incapacidad) justificándola.


# 24. Portal de Acceso Externo (Administradoras y Comités)

Permite que empresas administradoras y comités de condominios accedan a reportes financieros sin necesidad de ser usuarios operativos del sistema GESAC.

## 24.1 Acceso

- Desde el login principal → tarjeta "Empresas Administradoras / Comités".

## 24.2 Planes disponibles

  ——————— ——————— —————————
  **Plan**              **Precio**            **Condominios**

  Básico                \$299/mes + IVA       1 condominio

  Profesional           \$499/mes + IVA       Hasta 3 condominios

  Enterprise            \$999/mes + IVA       Ilimitados
  ——————— ——————— —————————

> Verifica estos precios Confirma que sigan vigentes con tu proveedor antes de compartirlos con un prospecto — los planes pueden actualizarse.

## 24.3 Registro, pago y solicitud de acceso

- Regístrate, elige tu plan, completa tus datos y paga con tarjeta vía Stripe — tu cuenta se activa automáticamente.

- Desde tu dashboard, "Solicitar acceso" y busca el condominio por nombre (mínimo 3 caracteres).

- El administrador del sistema revisa la solicitud y configura tus permisos por condominio.

## 24.4 Reportes disponibles

- Estado de Resultados financiero.

- Cartera de cobranza (vencida por período).

- Ingresos vs Gastos.

> Importante Los reportes disponibles dependen de los permisos que el administrador del sistema asigne a tu cuenta para cada condominio.

# 25. App Móvil GESAC

## 25.1 Para administradores

La app móvil GESAC (iOS) te permite, sin necesidad de una computadora:

- Consultar la cartera vencida en tiempo real de todos tus condominios.

- Ver el reporte de ingresos y gastos en tiempo real.

- Revisar el estado de resultados de cada propiedad que administras.

- Reservar amenidades a nombre de residentes (segmento habitacional).

Si administras varias empresas, la app permite alternar entre ellas desde la pantalla de selección posterior al inicio de sesión.

> Nota Los usuarios que ya tienen cuenta en el Portal de Empresas Administradoras / Comités (sección 24) pueden entrar a la app con las mismas credenciales — no necesitan un registro aparte.

## 25.2 Para condóminos

**Descargar e instalar**

1. Descarga "GESAC Condóminos" desde el App Store (iOS).

2. Abre la app y selecciona Crear cuenta.

3. Regístrate con tus datos y los de tu propiedad.

4. Inicia sesión con tu usuario y contraseña.

> Nota Tu condominio debe tener contratado el servicio GESAC Web. Si no logras registrarte, solicita a tu administrador que confirme que tu propiedad ya está dada de alta.

**Consultar cuotas, facturas y pagar**

- Revisa tus facturas de mantenimiento (y de renta de áreas comunes, si aplica).

- Descarga el CFDI de cada cuota pagada.

- Selecciona una cuota pendiente → "Pagar ahora" → captura tu método de pago → confirma.

> Nota GESAC no almacena los datos completos de tu tarjeta; son procesados directamente por la pasarela de pagos.

**Amenidades (segmento habitacional)**

- Consulta las amenidades disponibles de tu condominio (alberca, salón, gimnasio, etc.).

- Reserva el horario que necesites — la confirmación es automática si no hay traslape con otra reservación.

- Consulta y cancela tus reservaciones desde "Mis reservaciones".

**Avisos, tickets de soporte y publicidad**

- Consulta avisos importantes del condominio: asambleas, mantenimientos, recordatorios de pago.

- Levanta un ticket de soporte para reportar fallas o enviar comprobantes de pagos hechos fuera de la app.

- La app incluye un espacio de publicidad institucional; si tienes un negocio, puedes anunciarte desde el formulario de anunciante.

# 26. Preguntas Frecuentes

**¿Qué hago si olvidé mi contraseña?**

Usa la opción de recuperación en la pantalla de inicio de sesión, tanto en el sistema web como en la app móvil.

**¿Por qué no encuentro mi condominio al registrarme en la app?**

Ocurre cuando el condominio aún no ha sido dado de alta en el sistema, o el servicio GESAC Web no ha sido contratado. Contacta a tu administrador.

**¿Puedo usar la app en Android?**

Mientras tanto, usa GESAC Condóminos en iPhone.

**¿Cómo obtengo mi factura fiscal (CFDI)?**

Se genera automáticamente al registrar un pago y puede descargarse desde la app, o solicitarse al administrador vía ticket de soporte.

**¿Qué hago si mi pago no se refleja?**

Levanta un ticket de soporte adjuntando tu comprobante, para que el administrador lo verifique y registre manualmente si es necesario.

**¿Tengo que homologar mi catálogo contable antes de usar GESAC?**

No. Es opcional para el uso diario — solo es necesaria si quieres exportar pólizas contables para tu contador.

**¿Qué pasa si escribo algo que Sherlock no entiende?**

Te muestra un menú con las opciones disponibles según tu plan, para elegir con un clic.

**¿El empleado necesita instalar una app para marcar asistencia?**

No. Solo necesita abrir el link que le compartiste desde el navegador de su celular.

**¿Por qué no veo "Áreas Comunes" en el menú?**

Porque tu condominio está configurado en segmento Habitacional — ahí las amenidades no generan facturación, están incluidas en tu cuota de mantenimiento.

**¿Por qué me apareció una advertencia de presupuesto al solicitar un gasto?**

Porque la cuenta de gasto no tiene presupuesto capturado para el año en curso, o porque el monto solicitado excede lo que realmente queda disponible — la solicitud se guarda de todas formas, la advertencia es solo informativa (ver sección 17, Presupuestos, para el detalle completo).

**¿El corte de Sanitarios tiene que cerrarse a medianoche?**

No. Cada corte cubre el periodo real de un turno, sin importar si cruza la medianoche — el empleado lo cierra cuando termina su turno, no a una hora fija.

**¿Por qué no me deja guardar una propiedad con cuota en \$0?**

Es una validación intencional — evita que la facturación automática genere después una factura sin importe. Si un local no debe cobrarse mientras esté vacío, usa Pools de Vacancia (sección 5.5) en vez de dejarlo en \$0.

**¿Qué pasa si asigno un cliente a un local y no cambio su Estado?**

No importa qué hayas dejado seleccionado en Estado — en cuanto guardas con un cliente nuevo asignado, GESAC lo pone en "Ocupado" automáticamente (ver sección 3.4).

# 27. Contacto y Soporte

Para dudas adicionales, soporte técnico o información comercial:

- Sitio web: https://adminsoftheron.onrender.com/login/?next=/

- Dentro del sistema web: módulo de Ayuda.

- Dentro de la app: sección de Tickets de soporte.

*© 2026 GESAC — Created By JMEB. Todos los derechos reservados. · Manual de Usuario Completo, versión unificada Agosto 2026*
