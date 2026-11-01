# Manual de uso de Kidux

*[English version](../en/user-guide.md)*

Este manual es para el adulto que se ocupa de un ordenador con Kidux. Los
niños no necesitan manual: cada pantalla a la que pueden llegar se
explica sola.

## 1. Qué hace falta

- Un ordenador con **procesador de 64 bits**. Lo tiene casi cualquier PC o
  portátil fabricado a partir de 2008.
- Al menos **2 GB de memoria**. Con 4 GB va mejor.
- **32 GB de disco**, y el disco entero. Kidux guarda el sistema en una
  parte del disco y el trabajo de los niños en otra. Así el sistema se
  puede actualizar, o incluso reinstalar, sin tocar nada de lo que los
  niños han hecho.
- Una pantalla de al menos **1280 por 800** píxeles, mostrada al 100 %.
  Todas las pantallas de Kidux están hechas para caber enteras en ese
  tamaño. Mejor una pantalla con más sitio: **1920 por 1080** al 100 %, o
  una pantalla de alta densidad mostrada más grande, como 2560 por 1600 al
  150 % o la de un MacBook, 2880 por 1800 al 175 %, el tamaño que Kidux
  elige él solo para ella; cada una deja unos 1650 por 1030 de sitio o
  más. Los módulos de aprendizaje con paneles a los lados, como Step, Kig
  y Scratch, y los que llevan una guía al lado, funcionan en 1280 por 800
  pero van apretados, y con ese sitio van holgados. En una pantalla más
  pequeña que 1280 por 800, como 1366 por 768 o 1024 por 768, algunas
  pantallas de Kidux se desplazan, y algunos módulos de aprendizaje
  pueden tener partes ocultas o no funcionar bien. El tamaño al que se
  muestra todo se elige en el panel de adulto (sección 8).

## 2. Instalar Kidux

Hay dos formas de poner Kidux en un ordenador, y una tercera opción
para verlo funcionar antes de dedicarle ningún ordenador. Esta tabla
resume cuál conviene en cada caso:

| Lo que quieres | Qué hacer |
|---|---|
| **Instalar Kidux en un ordenador** | **Descarga el instalador**, grábalo en una memoria USB y arranca el ordenador desde ella. Es la forma habitual y la más rápida, y se explica a continuación, en [Con la imagen de Kidux](#con-la-imagen-de-kidux). |
| **Probarlo primero**, en el ordenador de todos los días | Descarga una imagen preparada para funcionar en un emulador, en Windows, macOS o Linux, con una familia ya creada. No se instala nada en el propio ordenador. La página [Probar Kidux en un emulador](try.md) explica cómo hacerlo. |
| **Instalarlo sobre un Debian** preparado por uno mismo | Se explica más abajo, en [Sobre Debian](#sobre-debian). El resultado es exactamente el mismo Kidux, pero el proceso lleva alrededor de una hora. |

### Con la imagen de Kidux

El instalador de Kidux es la imagen de una memoria USB: un solo
archivo, de unos 750 MB, con todo lo que Kidux necesita. Se graba en una
memoria, se arranca el ordenador desde ella y, en pocos minutos, Kidux
queda instalado en el disco completo del ordenador. Mientras instala no
necesita conexión a la red.

Ten en cuenta que se borra todo lo que haya en el disco del ordenador. Si
hay algo que quieras conservar, cópialo antes en otro sitio.

1. **Descarga el instalador.** Desde otro ordenador, descarga el archivo
   [kidux-amd64.iso](https://iso.kidux.org/kidux-amd64.iso). El nombre
   completo del archivo indica la versión de Kidux que instala. Si quieres
   comprobar que la descarga ha llegado entera, su suma SHA-256 está en
   [SHA256SUMS](https://iso.kidux.org/SHA256SUMS), y la firma de esa
   lista, hecha con la clave de Kidux, en
   [SHA256SUMS.sign](https://iso.kidux.org/SHA256SUMS.sign).

2. **Grábalo en una memoria USB** de 2 GB o más. Puedes usar un programa
   como [balenaEtcher](https://etcher.balena.io/): se elige el archivo, se
   elige la memoria y se pulsa grabar. Todo lo que hubiera en la memoria
   se borra. Una tarjeta SD, o cualquier otra unidad externa desde la que
   el ordenador pueda arrancar, sirve exactamente igual.

3. **Arranca el ordenador desde la memoria.** Conecta la memoria, enciende
   el ordenador y abre su menú de arranque. Normalmente se consigue
   pulsando F12, F11, F8, Esc o F2 justo después de encenderlo; en un Mac,
   manteniendo pulsada la tecla Opción. En ese menú, elige la memoria. Si
   el ordenador tiene activado el **arranque seguro** (Secure Boot), no
   hace falta desactivarlo: la memoria arranca tal cual.

4. **Elige el idioma.** El menú de Kidux ofrece dos opciones: **Instalar
   Kidux**, en español, e **Install Kidux**, en inglés. Si no eliges
   ninguna, la primera arranca sola a los diez segundos. Si la pantalla se
   queda negra o se ve mal, vuelve a arrancar el ordenador y elige
   **Gráficos seguros / Safe graphics**, que ofrece las mismas dos opciones
   con unos gráficos más sencillos.

   ![El menú de arranque de Kidux, con Instalar Kidux elegido](../images/es/install-boot-menu.png)

5. **Responde al instalador.** Sus pasos aparecen en la columna de la
   izquierda, y el botón **Siguiente** pasa de uno al siguiente. Esto es
   lo que pregunta cada paso:

   | Paso | Lo que pregunta |
   |---|---|
   | **Primeros pasos** | Nada. Comprueba que el ordenador tiene disco y memoria suficientes. |
   | **Ubicación** | La zona horaria. Se elige en el mapa. |
   | **Teclado** | La distribución del teclado, que se puede probar en el recuadro de debajo. No te preocupes si dudas: Kidux vuelve a preguntar su idioma y su teclado en su primer arranque. |
   | **Particiones** | Nada que elegir. El instalador borra el disco entero y lo divide como Kidux necesita: el sistema en una parte y el trabajo de los niños en otra. La página muestra cómo queda el disco antes y después. |
   | **Usuarios** | Una cuenta para ti, el adulto que cuida del ordenador. Se pide tu nombre, un nombre de usuario, el nombre del equipo (viene ya escrito `kidux`) y una contraseña, dos veces. Los niños tendrán sus propias cuentas dentro de Kidux. Esta contraseña tampoco es la que abre el panel de adulto, que se elige en el primer arranque. Deja sin marcar **Iniciar sesión automáticamente**: Kidux arranca siempre en su propia pantalla de entrada. |
   | **Resumen** | Muestra lo que va a ocurrir. El botón **Instalar** lo pone en marcha, tras una última pregunta de confirmación. |
   | **Instalar** | Una barra muestra el progreso. Tarda unos minutos. |
   | **Terminar** | Kidux ya está instalado. Con la casilla **Reiniciar ahora** marcada, el botón **Hecho** reinicia el ordenador. |

   La primera página del instalador:

   ![La página de bienvenida del instalador](../images/es/install-welcome.png)

   El disco, dividido como Kidux lo necesita:

   ![La página Particiones, con el disco antes y después](../images/es/install-partitions.png)

   Tu cuenta, la del adulto:

   ![La página Usuarios, rellena](../images/es/install-users.png)

   Lo que va a ocurrir:

   ![La página Resumen](../images/es/install-summary.png)

   Y el final:

   ![La página Terminar, con Reiniciar ahora marcado](../images/es/install-finished.png)

6. **Retira la memoria** cuando el ordenador se reinicie. Al arrancar,
   muestra el logo de Kidux y empieza su primer arranque. La sección
   siguiente, *El primer arranque*, describe lo que ocurre entonces.

### Sobre Debian

Kidux está construido sobre [Debian](https://www.debian.org/), y se
instala encima de un Debian 13 que no tenga nada más. Todo el proceso
lleva alrededor de una hora, casi toda de espera. Una parte se escribe en
una consola de texto, y cada línea que hay que escribir está aquí.

Se borra todo lo que haya en el disco del ordenador. Copia antes en otro
sitio lo que quieras conservar.

1. **Descarga Debian.** En otro ordenador, ve a
   [debian.org/download](https://www.debian.org/download) y descarga la
   imagen pequeña de instalación. Es un archivo con un nombre como
   `debian-13.x.0-amd64-netinst.iso`.

2. **Grábala en una memoria USB** de 1 GB o más, con un programa como
   [balenaEtcher](https://etcher.balena.io/): eliges el archivo, eliges la
   memoria y grabas. Se borra todo lo que haya en la memoria.

3. **Arranca el ordenador desde la memoria.** Conecta la memoria. Si el
   ordenador tiene dónde enchufar un cable de red, conecta uno también.
   Enciende el ordenador y abre su menú de arranque. Normalmente es pulsar
   F12, F11, F8, Esc o F2 nada más encender, o mantener la tecla Opción en
   un Mac. Elige la memoria, y después **Graphical install**. Ese primer
   menú está siempre en inglés; el idioma se elige en la pantalla
   siguiente.

   ![El primer menú del instalador de Debian](../images/es/install-debian-menu.png)

4. **Responde al instalador.** Va pregunta a pregunta, y se avanza con
   **Continuar**. Casi todas las preguntas se pueden dejar como vienen.
   Estas son las que le importan a Kidux:

   | El instalador pregunta | Respuesta |
   |---|---|
   | Idioma, país, teclado | Los tuyos. Kidux pregunta su propio idioma y teclado en su primer arranque. |
   | Red | Con cable no pregunta nada. Sin cable, elige tu wifi y escribe su contraseña. |
   | Nombre de la máquina y dominio | Cualquier nombre, `kidux` por ejemplo. El dominio, vacío. |
   | Clave del superusuario | Deja las dos casillas **vacías**. Así el usuario que se crea a continuación puede ocuparse del ordenador. |
   | Nombre, usuario y contraseña | Una cuenta para ti, el adulto. Los niños tendrán las suyas en Kidux. |
   | Particionado de discos | **Guiado - utilizar todo el disco**, el disco del ordenador, y **Separar la partición /home**: el sistema en una parte del disco y el trabajo de los niños en otra. Después, **Finalizar el particionado y escribir los cambios en el disco**, y **Sí** cuando pregunta si quieres escribir los cambios; viene marcado **No**. |
   | Réplica de Debian, proxy, encuesta de paquetes | Lo que viene elegido. |
   | Selección de programas | Desmarca **Entorno de escritorio Debian** y **GNOME**, y deja marcado solo **Utilidades estándar del sistema**. Sin escritorio: Kidux trae sus propias pantallas. |
   | Cargador de arranque GRUB | Solo lo pregunta en ordenadores antiguos. **Sí**, en el disco del propio ordenador. |

   La clave del superusuario, vacía:

   ![La pantalla de la clave del superusuario, con las dos casillas vacías](../images/es/install-debian-root-password.png)

   El esquema de particiones:

   ![El esquema de particionado, con «Separar la partición /home» elegido](../images/es/install-debian-partitions.png)

   Y los programas: solo las utilidades estándar.

   ![La selección de programas, con solo «Utilidades estándar del sistema» marcado](../images/es/install-debian-software.png)

   Cuando el instalador termine, quita la memoria y deja que el ordenador
   se reinicie.

5. **Entra en Debian.** El ordenador arranca en una pantalla de texto que
   pide un usuario. Escribe el nombre de usuario y la contraseña que diste
   al instalador.

6. **Instala Kidux.** Escribe estas líneas, de una en una. Las tres
   primeras descargan e instalan la dirección de la que vienen los
   paquetes de Kidux, y la clave con la que están firmados. Las dos
   últimas instalan Kidux.

   ```
   wget https://apt.kidux.org/bootstrap/stable/kidux-archive-keyring.deb
   wget https://apt.kidux.org/bootstrap/stable/kidux-apt-source.deb
   sudo apt install ./kidux-archive-keyring.deb ./kidux-apt-source.deb
   sudo apt update
   sudo apt install kidux-base
   ```

   La primera línea que empieza por `sudo` pide tu contraseña. La última
   enseña lo que va a instalar y pregunta si continúa: pulsa Intro. Tarda
   unos minutos.

   ![Las dos primeras líneas, escritas en la pantalla de texto de Debian](../images/es/install-debian-console.png)

7. **Si el ordenador va por wifi, traspasa la wifi a Kidux.** Con cable de
   red, sáltate este paso.

   El instalador de Debian escribió la wifi a la que se conectó en un
   archivo suyo, `/etc/network/interfaces`. El panel de adulto de Kidux
   tiene una página **Red** para conectarse a redes wifi y cambiarlas,
   pero no puede cambiar una red que esté escrita en ese archivo. Así que
   quítala del archivo ahora.

   Abre el archivo:

   ```
   sudo nano /etc/network/interfaces
   ```

   Se parece a esto. El nombre de tu tarjeta wifi empieza por `wl`, y el
   nombre de tu red está en la línea que empieza por `wpa-ssid`:

   ```
   # This file describes the network interfaces available on your system
   # and how to activate them. For more information, see interfaces(5).

   source /etc/network/interfaces.d/*

   # The loopback network interface
   auto lo
   iface lo inet loopback

   # The primary network interface
   allow-hotplug wlp3s0
   iface wlp3s0 inet dhcp
           wpa-ssid MiRed
           wpa-psk  su-contraseña
   ```

   Borra las líneas que nombran la tarjeta wifi: las que empiezan por
   `allow-hotplug` e `iface`, y las líneas de debajo que empiezan por
   `wpa-`. Deja el resto como está:

   ```
   # This file describes the network interfaces available on your system
   # and how to activate them. For more information, see interfaces(5).

   source /etc/network/interfaces.d/*

   # The loopback network interface
   auto lo
   iface lo inet loopback
   ```

   Guarda con Ctrl+O y Enter, y sal con Ctrl+X.

8. **Reinicia.**

   ```
   sudo reboot
   ```

   El ordenador muestra el logo de Kidux y arranca por primera vez. La
   sección siguiente describe lo que pasa entonces. Ahora que la wifi ya
   no está en el archivo, el ordenador no está en ninguna red hasta que te
   conectes de nuevo desde la página **Red** del panel de adulto (sección
   8).

## 3. El primer arranque

Cada vez que arranca, el ordenador muestra el logo de Kidux hasta que la
primera pantalla está lista.

![El logo de Kidux mientras arranca el ordenador](../images/es/boot-splash.png)

La primera vez que arranca, el ordenador se configura contigo. Lleva unos
minutos. No hace falta ningún atajo de teclado ni ninguna terminal: son
seis pantallas, una detrás de otra.

1. **Idioma.** Elige el idioma del ordenador. Cada idioma aparece escrito
   en sus propias palabras, para que encuentres el tuyo esté la pantalla
   en el idioma que esté.

   ![Elegir el idioma](../images/es/first-start-language.png)

2. **Teclado.** Elige el teclado que tiene tu ordenador. La pantalla se
   reinicia sola para usarlo. A partir de ahora, todas las contraseñas se
   escriben con este teclado, en todas las pantallas que piden una.

   ![Elegir el teclado](../images/es/first-start-keyboard.png)

3. **La contraseña de adulto.** Escríbela dos veces. Esta contraseña abre
   el panel de adulto, donde decides todo lo que tiene que ver con los
   niños. Elige una que los niños no puedan adivinar, y no dejes que te
   vean escribirla. No hay ninguna regla sobre su longitud ni sobre sus
   caracteres. Una más larga es, simplemente, más difícil de adivinar.

   ![Elegir la contraseña de adulto](../images/es/first-start-adult-password.png)

4. **Estadísticas de uso.** Cuando el ordenador busca actualizaciones, le
   dice al servidor de Kidux que es un ordenador con Kidux. Con este
   interruptor encendido, añade un identificador hecho solo para este
   ordenador, para que el proyecto lo cuente como un ordenador. No se
   envía nada más: ni nombre, ni versión, ni nada de ningún niño. Está
   encendido; apágalo si lo prefieres, ahora o más tarde en la página
   Sistema, en Avanzado. Pulsa **Continuar**.

   ![Compartir estadísticas de uso](../images/es/first-start-statistics.png)

5. **El primer niño.** Todo lo del niño está en una sola pantalla:

   - su nombre;
   - un dibujo con el que se reconozca;
   - su idioma;
   - su propia contraseña, escrita dos veces. Para un niño pequeño puede
     ser muy sencilla;
   - cómo puede usar el ordenador (sección 6). Empieza en una hora al
     día.

   Con el nombre y la contraseña basta. Pulsa **Añadir**.

   ![El primer niño](../images/es/first-start-child.png)

6. **Listo.** Aparece la pantalla de inicio, con el dibujo del niño. Todo
   se puede cambiar más adelante desde el panel de adulto, y allí se
   pueden añadir más niños.

   ![Todo está listo](../images/es/first-start-done.png)

## 4. La pantalla de inicio

El ordenador siempre arranca aquí. También vuelve aquí cuando un niño
sale.

![La pantalla de inicio, con el dibujo de cada niño](../images/es/sign-in.png)

Cada niño tiene su dibujo y su nombre. Para entrar, el niño toca su
dibujo y escribe su contraseña. En cuanto toca el dibujo, la pantalla
cambia al idioma de ese niño. Dos niños con idiomas distintos ven cada
uno el suyo.

Abajo, en letra pequeña, la pantalla dice qué versión de Kidux es esta:
por ejemplo, **Kidux 0.2.3**. Después de una actualización, el número
cambia. La pantalla de bloqueo también lo dice, bajo el logo.

En un portátil, la esquina de arriba a la derecha muestra la batería, el
sonido, la luz del teclado y el brillo de la pantalla, igual que la
pantalla de un niño (sección 5). La esquina está en esta pantalla, en la
de bloqueo y en las del adulto por igual. Las teclas del propio portátil
para esas cosas funcionan también en todas ellas.

![La pantalla pide la contraseña de un niño](../images/es/password.png)

Una contraseña equivocada nunca es una regañina. La pantalla dice que la
contraseña no es correcta, y deja al niño intentarlo otra vez.

![Una contraseña equivocada](../images/es/wrong-password.png)

Si el niño ya ha usado todo su tiempo del día, la pantalla se lo dice y le
ofrece **Pedir más tiempo a un adulto**. Se toca y se escribe la
contraseña de adulto. La pantalla dice entonces cuánto tiempo le queda al
niño, y ofrece quince, treinta o sesenta minutos, o el número que se
quiera. Se elige uno, y el niño entra.

![Un niño que ya ha gastado su tiempo](../images/es/time-spent.png)

Un día de la semana que no es del niño (sección 6), la pantalla le dice
que hoy el ordenador no es para él, y le ofrece el mismo **Pedir más
tiempo a un adulto**.

![Un día que no es del niño](../images/es/day-off.png)

![Un adulto añade minutos](../images/es/adult-gives-time.png)

En las esquinas de la pantalla hay dos botones más:

- **Adulto**, abajo a la izquierda, pide la contraseña de adulto y abre el
  panel de adulto.
- **Apagar**, abajo a la derecha, pregunta una vez y después apaga o
  reinicia el ordenador. Un niño siempre puede hacerlo.

![¿Apagar el ordenador?](../images/es/turn-off.png)

## 5. La sesión de un niño

### La pantalla del niño

Una vez dentro, el niño ve su propia pantalla y nada más. En ella hay:

- su dibujo y su nombre;
- el reloj;
- cuánto tiempo le queda hoy, si su tiempo está limitado. Se muestra como
  un reloj de arena con las horas y los minutos, por ejemplo **00:51**.
  Al dejar el puntero encima, o al tocarlo, lo dice con palabras: *Te
  quedan 51 minutos*;
- los módulos de aprendizaje que un adulto le ha activado, una ficha cada
  uno.

En un portátil, la esquina de arriba a la derecha muestra además lo que
tiene la máquina: la batería y su carga, el sonido, la luz del teclado y
el brillo de la pantalla. Los tres últimos son botones, y cada uno abre
un control deslizante. El del sonido tiene **Silenciar** debajo. Un
ordenador que no tenga alguna de estas cosas, sencillamente, no la
muestra.

A veces un módulo tiene algo que decirle al niño. Correo, por ejemplo,
cuando su servidor no contesta. Entonces sale una burbuja de la barra,
abajo a la derecha, encima de lo que esté abierto, y dice de qué módulo
viene. Se va sola a los pocos segundos. Una burbuja que avisa de algo que
ha ido mal puede quedarse hasta que el niño la cierra con su **×**.

La campana del extremo derecho de la barra guarda las últimas burbujas,
con la hora a la que llegó cada una, para que el niño pueda volver a leer
una que ya se fue. Un número junto a la campana dice cuántas han llegado
desde la última vez que se abrió la campana, y **Vaciar** deja la lista
vacía. Una burbuja nunca suena, y nunca viene de una web.

Un enlace de un módulo que lleva a internet, como la página de ayuda de un
programa, no abre nada. En su lugar, una burbuja dice *Eso abre internet,
que aquí está cerrado.*

![La pantalla de un niño](../images/es/launcher.png)

### Abrir un módulo

Cada módulo activado para el niño es una ficha, con su dibujo y su nombre
en el idioma del niño. El niño abre uno tocándolo. También funciona con
el teclado: Tab hasta las fichas, las flechas hasta la que quiere, e
Intro.

Cuando hay más fichas de las que caben en la pantalla, aparece una barra
a la derecha, y una sombra en la parte de abajo muestra que hay más
fichas debajo.

![Un módulo activado para el niño](../images/es/launcher-tile.png)

Un módulo se abre ocupando la pantalla, por encima de una barra que se
queda siempre en la parte de abajo. Puede haber varios módulos abiertos a
la vez, y el niño pasa de uno a otro como en cualquier ordenador. Tocar
la ficha de un módulo que ya está abierto lleva a él, en vez de abrirlo
otra vez.

![Dos módulos abiertos, y la barra](../images/es/module-two-open.png)

### Una guía al lado de un módulo

Algunos módulos vienen con una guía: lecciones escritas para el niño, con
pasos que seguir, qué mirar e ideas para continuar. La guía se abre a la
derecha cuando se abre el módulo, y el módulo ocupa el resto de la
pantalla.

**Plegar**, arriba de la guía, la pliega en una tira estrecha pegada al
borde, para dejar más sitio al módulo. Un clic en la tira, o en **Guía**
en la barra, la abre otra vez, en la lección en la que estaba el niño.

Para un niño con ventanas, la guía se queda abierta mientras haya abierto
algún módulo que tenga guía, y enseña la del módulo que está en uso. El
nombre de arriba de la guía es una lista para elegir otra guía, y
**Fijar** mantiene la elegida uses la ventana que uses.

Una lección puede tener una *misión*: un archivo del módulo, a medio
hacer, con lo que probar escrito dentro. La primera vez que se abre la
guía, las misiones se copian en los **Documentos** del niño, en una
carpeta con el nombre del módulo. La lección dice cómo abrir su misión
desde el propio módulo, con **Archivo**, **Abrir**.

Kig, Step y Kalzium tienen guía.

![Una guía al lado de Kig](../images/es/module-kig-guide.png)

### La barra

La barra de abajo tiene siempre:

- **Inicio**, que vuelve a la pantalla del niño;
- un botón por cada módulo abierto, con el que está en pantalla marcado.
  Los botones ocupan todo el sitio que hay entre **Inicio** y el tiempo
  que queda.

Mientras hay un módulo en pantalla, la barra muestra también el tiempo
que queda (el reloj de arena), **Cerrar** y **Bloquear**.

**Cerrar** cierra el módulo que está en pantalla. Primero se le pide al
módulo, como a cualquier programa cuando se cierra su ventana, para que
un módulo con trabajo sin guardar pueda avisar. Si el módulo sigue
abierto diez segundos después, la barra pregunta si cerrarlo igualmente:

- **Cancelar** lo deja abierto;
- **Cerrarlo igualmente** lo cierra. Lo que no se haya guardado se
  pierde.

![Un módulo que no se ha cerrado, y la barra preguntando](../images/es/launcher-close-question.png)

### El teclado

Unas pocas teclas hacen lo mismo que los botones de la barra:

- La **tecla de Windows** (la del logotipo; **⌘** en un teclado de Mac),
  pulsada sola, vuelve a Inicio.
- **Alt+Tab** recorre los módulos abiertos en el orden que tienen en la
  barra. Pasa al siguiente a la derecha del módulo que está en pantalla,
  y del último vuelve al primero. Desde la pantalla del niño, pasa al
  primero. Mientras se mantiene **Alt**, cada pulsación de **Tab**
  ilumina el siguiente módulo en la barra, y al soltar **Alt** se pasa al
  iluminado. **Alt+Mayúsculas+Tab** recorre al revés. Alt+Tab nunca lleva
  a la pantalla del niño: para eso está la tecla de Windows. Con un solo
  módulo abierto, y en pantalla, no hace nada.
- **Alt+F4** es **Cerrar**. Pulsada otra vez mientras la barra pregunta,
  cierra el módulo igualmente.

Al dejar el puntero sobre un botón de la barra, aparece la tecla que hace
lo mismo, para que el niño pueda aprender las teclas. En un Mac, donde F4
necesita la tecla fn, **Cerrar** dice **Alt+(fn)F4**. El módulo al que
iría Alt+Tab dice **Alt+Tab**.

### Las teclas propias de un portátil y su tapa

Las teclas propias de un portátil para el brillo de la pantalla, la luz
del teclado y el sonido (más alto, más bajo y silencio) hacen lo que
dicen, dentro de cualquier módulo. La esquina de la pantalla del niño
muestra el nuevo nivel al momento.

Cerrar la tapa bloquea la sesión del niño y apaga la pantalla y la luz
del teclado; después el ordenador se duerme, y al minuto se apaga
guardando, como dice la página **Dormir y tapa** del panel de adulto
(sección 8). Al abrir la tapa se despierta y la pantalla se enciende de
nuevo, con la luz tan fuerte como estaba, en la pantalla de bloqueo,
donde el niño escribe su contraseña para seguir. El tiempo no cuenta
mientras la tapa está cerrada.

Las mismas teclas funcionan en la pantalla de inicio y en la de bloqueo,
y cerrar la tapa allí también apaga la pantalla y la luz del teclado.

### Los archivos, bloquear y salir

Un archivo que el niño hace en un módulo queda guardado en sus propias
carpetas, donde cualquier otro módulo puede abrirlo.

![Inicio, con un módulo aún abierto en la barra](../images/es/launcher-with-module-open.png)

Abajo, en la pantalla del niño, hay tres botones:

- **Bloquear**, abajo a la izquierda, bloquea la pantalla al momento. Así
  es como un niño se levanta sin gastar tiempo: el tiempo no cuenta
  mientras la pantalla está bloqueada, y todo se queda exactamente como
  estaba.
- **Salir** cierra la sesión y vuelve a la pantalla de inicio. Antes
  pregunta si el trabajo del niño está guardado, porque salir cierra
  todos los módulos.
- **Apagar** hace aparecer la pantalla de bloqueo, desde la que se puede
  apagar el ordenador.

Una sesión que se deja sola también se bloquea sola. Tras cinco minutos
sin que nadie toque el teclado ni el ratón, la pantalla se bloquea, como
haría un salvapantallas. Un módulo que se mueve solo no es una excepción.
A los diez minutos la pantalla se apaga, y la luz del teclado con ella.
Esto pasa en todas las pantallas del ordenador, también en la de inicio y
en la de bloqueo, y el primer toque las vuelve a encender. Un adulto
puede cambiar los dos tiempos en la página **Sistema** del panel de
adulto (sección 8).

Bloquear la pantalla deja cada módulo exactamente donde estaba. Salir,
desde la pantalla del niño o desde la pantalla de bloqueo, cierra todos
los módulos con la sesión, así que conviene guardar antes.

![Salir pregunta antes](../images/es/log-out.png)

### Cuando el tiempo está a punto de acabarse

Diez, cinco y un minuto antes de que se le acabe el tiempo, una burbuja
de Kidux sale de la barra y le dice al niño que guarde su trabajo. Se
queda hasta que el niño la cierra, y la siguiente ocupa su sitio. Cuando
el tiempo se acaba, la pantalla de bloqueo aparece sola.

![Se ha acabado el tiempo](../images/es/time-is-up.png)

## 6. El tiempo

Cada niño usa el ordenador de una de tres maneras. Un adulto elige cuál:

- **Siempre que quiera.** No hay límite. El ordenador cuenta igualmente
  cuánto tiempo pasa el niño, para que un adulto pueda verlo.
- **Un tiempo fijo cada día.** Tantos minutos al día. El tiempo cuenta
  mientras la sesión está desbloqueada, haga algo el niño o no, y se
  detiene mientras la pantalla está bloqueada. El día empieza de nuevo a
  las cuatro de la madrugada, no a medianoche, para que una sesión de
  tarde no quede partida en dos. El tiempo extra que dé un adulto un día
  así dura hasta que acaba ese día.
- **Solo cuando un adulto lo permita.** El niño no puede entrar hasta que
  un adulto le dé tiempo, en la pantalla de inicio. El tiempo dado así se
  guarda hasta que se usa, aunque pasen días.

Las dos primeras maneras valen los **días** de la semana que marque un
adulto. Para un niño nuevo están marcados todos. Los demás días el
ordenador no es del niño: no puede entrar si un adulto no le da tiempo, y
ese tiempo dura hasta que acaba el día. Un niño que siga usando el
ordenador cuando empieza uno de esos días, a las cuatro de la madrugada,
encuentra la pantalla bloqueada, igual que cuando se le acaba el tiempo.

Dos cosas que conviene saber:

- El tiempo cuenta mientras la sesión está desbloqueada. Una sesión que
  se deja abierta durante la cena gasta el tiempo del día. Conviene que el
  niño bloquee la pantalla siempre que se levante.
- El tiempo ya gastado se recuerda aunque el ordenador se reinicie, se
  vaya la luz o el sistema falle.

## 7. La pantalla de bloqueo

La pantalla de bloqueo aparece sobre la sesión de un niño cuando se le
acaba el tiempo, cuando el niño bloquea la pantalla, cuando la sesión se
queda unos minutos sin que nadie la toque, cuando se cierra la tapa de un
portátil, y siempre que alguien pulsa el botón de encendido del
ordenador. Lo que el niño estaba haciendo se queda exactamente como
estaba, debajo, y nada suyo sigue funcionando.

![La pantalla de bloqueo](../images/es/lock-screen.png)

La pantalla de bloqueo ofrece cuatro cosas:

- **Continuar.** El niño escribe su contraseña y sigue, mientras le quede
  tiempo.
- **Adulto.** Se escribe la contraseña de adulto, y después se elige una
  de cuatro cosas:
  - **dar más tiempo**, viendo cuánto le queda al niño;
  - **desbloquear para guardar el trabajo**, que desbloquea la pantalla
    unos minutos sin contarlos, para que el niño guarde y vuelva a
    bloquear;
  - **salir**, que cierra la sesión;
  - el **panel de adulto** (sección 8).
- **Salir.** El niño escribe su contraseña y la sesión se cierra.
- **Apagar.** Pregunta una vez y después apaga el ordenador.

![Lo que puede hacer un adulto en la pantalla de bloqueo](../images/es/lock-adult-options.png)

El botón de encendido nunca apaga el ordenador por sí solo. Siempre hace
aparecer esta pantalla. Así, una contraseña solo se escribe en una
pantalla que es de verdad de Kidux, y nunca en algo que un programa del
niño haya dibujado para parecerse a ella.

## 8. El panel de adulto

### Abrirlo y cerrarlo

Pulsa **Adulto** en la pantalla de inicio, o **Adulto** y después **Panel
de adulto** en la pantalla de bloqueo, y escribe la contraseña de adulto.
El panel ocupa toda la pantalla. Se cierra con **Cerrar**, con la tecla
Escape, o solo, tras cinco minutos sin tocarlo (o tras los minutos que
diga la página **Sistema** para un ordenador que se deja solo). Nadie
puede dejarlo abierto sin querer.

Una costumbre mantiene la contraseña de adulto a salvo: **pulsa el botón
de encendido del ordenador antes de escribirla**, siempre que un niño
haya estado usando el ordenador. El botón de encendido siempre hace
aparecer la pantalla de bloqueo, que es de Kidux. Así, la pantalla en la
que escribes nunca es algo que haya dibujado un programa de un niño.

El panel tiene cuatro páginas: **Niños**, **Módulos**, **Sistema** y
**Red**. Cada página cabe en una sola pantalla, y todo se cambia en el
sitio, sin ir de una pantalla a otra.

Cuando una página tiene más de lo que cabe en la pantalla, con muchos
niños o muchos módulos, o en una pantalla pequeña, aparece una barra a su
derecha o en la parte de abajo, y una sombra en el borde por donde sigue
la página. Arrastra la barra, o desplázate, para ver el resto. Todas las
pantallas de Kidux hacen lo mismo.

### Niños

Arriba de la página están todos los niños, con el elegido marcado, y
**Añadir un niño**.

Debajo está el tiempo del niño elegido:

- cuánto tiempo ha usado hoy;
- botones para **darle más tiempo** en ese momento;
- **Le queda hoy**: los minutos que le quedan. Puedes cambiarlos a
  cualquier número, cero incluido, y pulsar **Fijar**. Ponerlos a cero
  termina su tiempo ya, aunque esté usando el ordenador: la pantalla de
  bloqueo sale al momento.

Y debajo está todo lo del niño:

- su nombre;
- su dibujo;
- su idioma;
- una contraseña nueva, si quieres cambiarla;
- cómo puede usar el ordenador (sección 6), y los **días** de la semana
  en que vale eso, de lunes a domingo;
- **Ventanas**, que se explica más abajo.

Cambia lo que quieras y pulsa **Guardar**. Si algo no se puede guardar,
queda marcado en su sitio, y el resto sí se guarda. **Añadir un niño**
muestra la misma página, vacía.

**Eliminar** pregunta una vez, en la misma página. Eliminar a un niño
borra su cuenta y todo lo que contiene. **Eliminar, pero conservar sus
archivos** borra la cuenta pero deja los archivos del niño en el
ordenador. Un niño que está dentro de su sesión no se puede eliminar
hasta que salga.

![Un niño, en el panel de adulto](../images/es/panel-children.png)

![El dibujo de un niño, cambiado y guardado](../images/es/panel-child.png)

### Ventanas

**Ventanas** está desactivado para un niño nuevo. Entonces cada módulo de
aprendizaje ocupa la pantalla por encima de la barra, que es lo más
sencillo para un niño pequeño.

Con **Ventanas** activado, los módulos del niño se abren en ventanas,
varias a la vez, como en cualquier ordenador:

- cada ventana tiene una barra de título para moverla, bordes para
  cambiarle el tamaño, y botones para minimizarla, maximizarla y
  cerrarla;
- lo que se copia en una ventana se puede pegar en otra;
- la barra tiene un botón por cada ventana. La que está en uso aparece
  marcada, y una minimizada, más clara. Tocar un botón trae su ventana
  delante. Cuando hay más botones de los que caben, una flecha a cada
  lado muestra los demás;
- **Inicio**, y la tecla de Windows, muestran el escritorio: todas las
  ventanas minimizadas y las fichas del niño a la vista. Tocar una ficha,
  o el botón de una ventana en la barra, trae las ventanas de vuelta como
  estaban, con la pedida delante. Una ventana que el niño minimizó sigue
  minimizada.

El cambio se aplica la próxima vez que el niño entra.

Algunos módulos de aprendizaje, un navegador web de verdad por ejemplo,
solo funcionan con ventanas. Lo dicen en la página **Módulos**, donde no
se pueden activar para un niño sin ventanas.

![Dos ventanas a la vez, para un niño con ventanas](../images/es/windows-desk.png)

### Módulos

La página **Módulos** muestra cada módulo de aprendizaje instalado en el
ordenador, con su nombre y para qué sirve. Junto al nombre, en letra más
pequeña, están las edades para las que está pensado el módulo y su
versión. Debajo, cuando los hay, **Módulos previos recomendados:** nombra
los módulos que conviene hacer antes. Es un consejo: cualquier módulo se
puede activar para cualquier niño.

Las dos listas están ordenadas según la edad recomendada, desde los módulos para los niños más pequeños hacia los de los mayores. La casilla superior, **Buscar un módulo**, filtra las listas para mostrar solo los módulos cuyo nombre o descripción coincidan con el texto introducido.

Cada módulo tiene un interruptor para cada niño, bajo el dibujo del niño.
Un interruptor se guarda en cuanto lo cambias, y la pantalla del niño lo
sigue al momento, aunque esté usando el ordenador.

![Un módulo activado para un niño](../images/es/panel-modules.png)

Debajo de los módulos instalados, **Añadir módulos** muestra los módulos
de aprendizaje que ofrece Kidux y que aún no están en el ordenador, con
las mismas edades y módulos que hacer antes.

- **Instalar** añade uno. El módulo sube al momento entre los instalados,
  con una barra que enseña cuánto le falta, donde irán sus
  interruptores. Al terminar, el módulo queda apagado para todos los
  niños, y una palabra abajo en la página lo dice. Mientras tanto la
  página sigue siendo tuya: puedes moverla, e instalar o eliminar otros
  módulos. Esperan su turno, cada fila diciendo *Esperando…*, y van uno
  detrás de otro.
- **Ajustes** aparece en la fila de un módulo que tiene ajustes. Abre lo
  que un adulto puede ajustar en ese módulo para cada niño: una columna
  por niño, y cada ajuste con lo que hace escrito debajo. Un cambio se
  guarda en cuanto se hace. El ajuste de BASIC es *Escríbemelo*: apagado,
  el niño escribe todos los programas de la guía.
- **Eliminar**, al final de la fila de un módulo instalado, pregunta una
  vez, en esa misma fila, y quita el módulo del ordenador, junto con los
  programas que se instalaron solo para él. Lo que cada niño hizo con él
  se queda en sus propias carpetas. Lo que el módulo guardaba para cada
  niño, como su avance y sus ajustes, también se queda, y el módulo lo
  encuentra de nuevo si se vuelve a instalar.
- **Buscar módulos** pregunta a Kidux qué ofrece ahora. Necesita conexión
  a internet.

Los módulos solo se instalan y se quitan cuando no hay ningún niño dentro
de su sesión, para que nada de lo que esté usando cambie mientras tanto.

![Módulos de aprendizaje para añadir](../images/es/panel-modules-available.png)

### Sistema

La página **Sistema** contiene, de arriba abajo:

- **La versión de Kidux**, y debajo, más pequeña, la versión de cada una
  de sus partes. Esto es lo que hay que dar a quien te esté ayudando a
  averiguar qué ha fallado. Junto a la versión están las actualizaciones
  (sección 10).
- **La contraseña de recuperación.** Sirve para arrancar el ordenador de
  otra forma desde el menú de arranque, si alguna vez Kidux no arranca
  (sección 11). Apúntala en un lugar seguro.
- **Cambiar la contraseña de adulto**, escribiendo la actual y la nueva
  dos veces.
- **El idioma y el teclado del ordenador.**
- **El tamaño de todo lo que hay en la pantalla.** Es **Automático** hasta
  que eliges, y el tamaño que eso da aparece entre paréntesis: por
  ejemplo, **Automático (175 %\*)**. Automático quiere decir tan grande
  como permite la pantalla dejando sitio de sobra. Elige un tamaño menor
  para tener más sitio en una pantalla grande, o uno mayor para ver todo
  más grande.

  Los tamaños marcados con \* no son múltiplos enteros de 100 %. Un
  módulo de aprendizaje hecho para X11, el sistema antiguo de pantalla de
  Linux, puede verse borroso con uno de ellos. Si pasa, elige un tamaño
  sin \*.

  Un tamaño mayor deja menos sitio. A 200 %, una pantalla de 1280 por 800
  tiene el sitio de una de 640 por 400. Kidux está hecho para el sitio de
  1280 por 800. Con menos, algunas de sus pantallas se desplazan, y
  algunos módulos de aprendizaje pueden no verse bien.
- **Si se deja solo**: tras cuántos minutos sin tocarlo se bloquea sola
  la sesión de un niño (cinco, para empezar), y tras cuántos se apaga
  cualquier pantalla del ordenador (diez). El primer número es también el
  tiempo que este panel sigue abierto. Cambia cualquiera de los dos
  números y pulsa **Fijar**. El panel toma los números nuevos al momento;
  la sesión de un niño los toma la próxima vez que el niño entra.

El idioma, el teclado y el tamaño se guardan en cuanto los eliges:

- en la pantalla de inicio, se aplican al cerrar el panel. La pantalla
  vuelve a arrancar con ellos, lo que tarda un momento;
- en la pantalla de bloqueo, se aplican la próxima vez que arranca una
  pantalla, porque la pantalla de bloqueo no puede volver a arrancar sobre
  la sesión de un niño;
- la pantalla de un niño los toma la próxima vez que el niño entra.

![El sistema, en el panel de adulto](../images/es/panel-system.png)

### Avanzado

**Avanzado**, al final de la página Sistema, es para cómo se mueve el
puntero de este ordenador, y para cuando algo no funciona en este
ordenador en concreto.

**Velocidad del puntero** y **Desplazar con dos dedos** tienen cinco
pasos cada uno, de *Mucho más lento* a *Mucho más rápido*, y se guardan
en cuanto se elige uno. Se aplican a la sesión de un niño a partir de la
próxima vez que un niño entra. La pantalla de inicio, la de bloqueo y
este panel siguen con los ajustes del propio ordenador. Dos dedos en un
panel táctil desplazan la página. En *Normal* la desplazan la mitad que
la mayoría de los ordenadores, que va bien con los movimientos pequeños
de un niño, y *Mucho más rápido* es lo que hacen la mayoría de los
ordenadores. Prueba un paso con los dedos del propio niño antes de
quedártelo.

Las **Opciones de Chromium** son para un módulo de aprendizaje hecho de
páginas web, o para ScratchJr, que lleva Chromium dentro, cuando se ve
mal en la pantalla de este ordenador: con manchas de ruido o restos de
imágenes, o con una imagen que solo cambia al mover el puntero. Una
opción escrita en el cuadro, una por línea, cambia cómo dibuja Chromium.
Se aplica la próxima vez que se abre el módulo.

Debajo del cuadro, la página enumera las opciones que merece la pena
probar, en el orden en que probarlas, cada una con lo que hace. Puedes
seleccionar sus letras y copiarlas en el cuadro. Deja el cuadro vacío
salvo que sepas qué opción necesita tu ordenador: vacío es lo que Kidux
hace por su cuenta.

![Avanzado: el puntero y las opciones de Chromium](../images/es/panel-system-advanced.png)

### Dormir y tapa

**Dormir y tapa**, junto a **Avanzado** al final de la página Sistema, es
para lo que hace el ordenador al cerrar la tapa, y cuando nadie lo usa
durante un buen rato. Conoce dos formas de descansar:

- **Dormir**: el ordenador para casi todo, y despierta al momento, donde
  estaba, al abrir la tapa o pulsar una tecla. Sigue gastando algo de
  batería.
- **Apagar guardando**: el ordenador escribe en su disco todo lo que tiene
  abierto y se apaga. No gasta batería, y al encenderlo de nuevo vuelve a
  empezar donde estaba, algo más despacio que al despertar.

**Al cerrar la tapa** puede ser:

- **Dormir y, al minuto, apagar guardando**, que es lo que hace Kidux
  mientras no elijas otra cosa: cerrada un momento, el ordenador despierta
  al momento; cerrada más rato, está apagado y no gasta nada.
- **Dormir**.
- **Nada**: la tapa solo bloquea la sesión y apaga la pantalla.

Hace lo mismo con batería que enchufado. Con otra pantalla conectada,
cerrar la tapa solo apaga la pantalla del portátil, y el ordenador sigue
despierto. La elección se guarda, y se aplica, en cuanto se hace.

**Si sigue sin usarse** es lo que pasa cuando nadie toca el ordenador
durante unos minutos, veinte para empezar, después de que se apague la
pantalla (la fila **Si se deja solo** de la página Sistema): **Dormir y,
al minuto, apagar guardando**, **Dormir** o **Solo apagar la pantalla**.
Elige una y los minutos, y pulsa **Fijar**. Las pantallas de inicio y de
bloqueo lo toman la próxima vez que empiezan, la sesión de un niño la
próxima vez que el niño entra. No pasa nada mientras se reproduce un vídeo
o un programa pide que el ordenador siga despierto. Cada pantalla cuenta
sus propios minutos: la sesión de un niño que se deja sola se bloquea
primero, y la pantalla de bloqueo cuenta entonces desde el principio.

Antes de que el ordenador se duerma, por lo que sea, la sesión de un niño
se bloquea, así que el tiempo de un niño nunca se gasta mientras el
ordenador duerme.

Apagar guardando necesita un ordenador que pueda hacerlo: un espacio de
intercambio (swap) en su disco con sitio para lo que el ordenador tiene en
memoria, y Secure Boot desactivado en los ajustes del firmware del
ordenador, porque con Secure Boot activado Linux no deja guardar la
memoria en el disco. El instalador de Kidux crea un fichero de
intercambio del tamaño de la memoria, hasta 4 GB; un ordenador con más
memoria en uso que eso no puede apagar guardando. Cuando este ordenador no puede, la página
solo ofrece **Dormir**, y dice por qué en una línea. Una elección hecha
antes se conserva, y se hace como **Dormir**.

### Red

La página **Red** muestra cómo está conectado este ordenador:

- **Conexión**: cada conexión en una línea, wifi o cable, con el nombre
  de la red, su señal y la dirección del ordenador, o **Sin conexión**.
- **Router**: si el router, el aparato por el que pasa la conexión,
  responde.
- **Mirar otra vez** vuelve a preguntar al router y busca de nuevo redes
  wifi. La página lo hace sola al abrirse.

Cuando la wifi del ordenador se puede cambiar desde aquí, debajo aparecen
las redes wifi al alcance, con la que está en uso primero. Cada una
muestra su señal, y un candado si tiene contraseña.

- **Conectar** se conecta a una red. Cuando la red necesita contraseña,
  la página la pide en la misma línea. El ordenador guarda la contraseña,
  y desde entonces vuelve a conectarse a la red por su cuenta, antes de
  que nadie entre.
- **Olvidar** hace que el ordenador deje de conectarse a una red por su
  cuenta. Pregunta antes.

Cambiar de red puede dejar sin conexión los módulos de los niños un
momento.

La página puede conectarse a la red de una casa o de una cafetería, con
contraseña o sin ella. La red de una oficina o de un colegio que pide un
nombre de usuario propio no se puede configurar aquí.

![La página Red](../images/es/panel-network.png)

### Una wifi configurada al instalar Debian

Si la página Red dice que la wifi se configuró al instalar Debian,
muestra la conexión pero no puede cambiarla, porque el instalador de
Debian configuró la wifi a su manera. Para cambiarla desde la página, hay
que traspasarla una vez. Hazlo en el propio ordenador, no desde otro
ordenador conectado a él por esa wifi.

1. Abre una consola de texto. La sección 11 explica cómo.

2. Abre el archivo del instalador:

   ```
   sudo nano /etc/network/interfaces
   ```

3. Busca las líneas que empiezan por `allow-hotplug` o `iface` y nombran
   la tarjeta wifi. Su nombre empieza por `wl`. Borra esas líneas, y las
   líneas de debajo que empiezan por `wpa-`. Guarda el archivo.

4. Reinicia el ordenador:

   ```
   sudo reboot
   ```

Con el reinicio termina la manera del instalador de llevar la wifi. Desde
entonces, la tarjeta wifi la lleva Kidux. Cuando vuelva la pantalla de
inicio, abre el panel de adulto, ve a **Red** y conéctate a la wifi desde
la página, con su contraseña. A partir de ahí, la página puede cambiarla.

## 9. Módulos de aprendizaje

Cada módulo de aprendizaje es algo que un niño puede abrir desde su
pantalla. Un adulto activa cada módulo para cada niño, en la página
**Módulos** del panel de adulto (sección 8).

Algunos módulos están hechos de páginas web. Se abren a toda pantalla por
encima de la barra, en el navegador Chromium, sin barra de direcciones ni
pestañas, y solo muestran sus propias páginas. Un enlace que salga de
ellas a cualquier otro sitio no lleva a ninguna parte. Las palabras del
propio Chromium, en la página que muestra en lugar de una bloqueada o en
sus menús, están en el idioma del niño. Chromium es un programa grande,
de unos 300 MB, y llega con el primer módulo de este tipo.

Unos pocos módulos son una puerta a un sitio web de internet. Muestran
ese sitio y nada más de internet. Un enlace a cualquier otro sitio no
lleva a ninguna parte, y Chromium enseña una página que dice que está
bloqueado. Su nombre y su descripción dicen qué sitio abren y qué pide,
como una cuenta o una suscripción, para que el adulto lo sepa antes de
activarlo. Necesitan internet siempre que se usan.

Los módulos cuyo nombre empieza por **[Prueba]** existen para comprobar
que Kidux funciona, no para que los use un niño. Uno que dice **Una
carpeta, no de un paquete** se copió en el ordenador a mano en vez de
instalarse; **Eliminar** quita su carpeta.

### GCompris

**GCompris** son más de cien actividades para niños de dos a diez años:
leer y escribir, contar, los colores y las formas, y aprender a usar el
teclado y el ratón, cada una un pequeño juego. Habla el idioma del niño.

Sus voces y algunos de sus dibujos no están en el ordenador al principio.
GCompris los descarga él solo de internet las primeras veces que se usa,
así que entonces necesita conexión. Funciona sin ellos hasta que han
llegado. El panel lo dice antes de instalar GCompris.

GCompris ocupa toda la pantalla por encima de la barra. El botón
**Inicio** de la barra lleva al niño de vuelta a sus otras cosas.

![GCompris](../images/es/module-gcompris.png)

Más en [su página](modules/gcompris.md).

### Tux Typing

**Tux Typing** enseña a un niño a escribir a máquina. Del cielo caen
letras y palabras, y el niño atrapa cada una escribiéndola, cada nivel un
poco más difícil. Sus menús están en el idioma del niño, y también las
palabras que caen: un niño que habla español atrapa palabras en español.
Es para niños de seis a doce años. GCompris, que enseña primero las
letras del teclado, es un buen comienzo antes. Su menú **Lecciones** trae
el curso de mecanografía de Kidux: catorce lecciones que enseñan a escribir
con los diez dedos, fila a fila, y al final las vocales con tilde. En cada
práctica, el teclado dibujado muestra escritas solo las teclas que se
practican.

Tux Typing guarda sus puntuaciones y sus ajustes para sí, no en las
carpetas del niño. Al quitar el módulo se conservan para cuando vuelva.

![Tux Typing](../images/es/module-tuxtype.png)

Más en [su página](modules/tuxtype.md).

### ScratchJr

**ScratchJr** es Scratch para los más pequeños, de cinco a siete años.
Los personajes se mueven, hablan y juegan cuando el niño encaja bloques
con dibujos, sin una palabra que leer. Es la propia aplicación del MIT,
tal como su comunidad la ha llevado a los ordenadores, y trae consigo su
propia copia del motor de un navegador web: unos 380 MB.

Los proyectos del niño se guardan en una carpeta de sus **Documentos**,
**ScratchJR**, que ScratchJr crea la primera vez que se abre. Quitar el
módulo los deja ahí.

![ScratchJr](../images/es/module-scratchjr.png)

Más en [su página](modules/scratchjr.md).

### Juegos de Blockly

Los **Juegos de Blockly** son rompecabezas que enseñan las ideas de
programar con bloques, cada uno un paso más difícil: guiar a un personaje
por un laberinto, hacer volar un pájaro, dibujar con una tortuga, hacer
una película y hacer música. Son para niños de seis a doce años que ya
leen un poco. Están en el idioma del niño, y funcionan sin internet. Los
juegos recuerdan hasta dónde ha llegado el niño, y al quitar el módulo se
conserva para cuando vuelva.

![Juegos de Blockly](../images/es/module-blockly-games.png)

Más en [su página](modules/blockly-games.md).

### Scratch

**Scratch** es el editor que los niños usan en el colegio para hacer
juegos, historias y animaciones encajando bloques. Es el propio editor de
Scratch, en el idioma del niño, sin la comunidad de la web de Scratch:
nada de lo que hace un niño se comparte, y nadie más puede verlo. Es para
niños a partir de ocho años. ScratchJr, para los más pequeños, es un buen
comienzo antes.

Su biblioteca de personajes, fondos y sonidos viene de los servidores de
la Scratch Foundation cuando el niño la abre, así que entonces necesita
internet. Todo lo demás funciona sin ella. Los vídeos de los tutoriales
no se reproducen: están en una página web, y un módulo solo muestra sus
propias páginas.

Para guardar un proyecto, el niño elige **Archivo** y después **Guardar
en tu ordenador**. Se abre una ventana con las carpetas del niño, en
**Descargas**, para elegir dónde guardar el proyecto y con qué nombre, y
**Guardar** lo guarda. **Archivo** y después **Cargar desde tu ordenador**
abre la misma ventana para escoger un proyecto. Un proyecto guardado
desde Scratch se abre también en TurboWarp, y al revés.

![Scratch](../images/es/module-scratch.png)

Más en [su página](modules/scratch.md).

### TurboWarp

**TurboWarp** es Scratch más rápido: el mismo editor, los mismos bloques
y los mismos archivos de proyecto, con un compilador que hace funcionar
los proyectos muchas veces más deprisa. Elígelo en lugar de Scratch en un
ordenador más lento, o cuando Scratch no funcione bien en este. Lo dicho
de Scratch vale también para TurboWarp: su biblioteca viene de internet,
y un proyecto se guarda en las carpetas del niño, elegidas en una
ventana, y se vuelve a abrir desde ellas. Un proyecto se abre solo desde
un archivo. TurboWarp no puede traerlo de la web de Scratch por su
número.

![TurboWarp](../images/es/module-turbowarp.png)

Más en [su página](modules/turbowarp.md).

### BASIC

**BASIC** es el lenguaje que hablaban los primeros ordenadores de casa, y
sigue siendo una buena forma de empezar a escribir programas. El módulo
es un pequeño ordenador de aquella época a la izquierda, y una guía para
usarlo a la derecha. Es para niños de ocho a catorce años que ya leen
bien, en el idioma del niño, y no necesita nada de internet.

La mitad izquierda tiene tres partes: arriba el editor, donde el niño
escribe el programa; una fila de botones; y debajo la pantalla, donde el
programa enseña lo que hace. **Ejecutar** pone el programa en marcha, y
Ctrl+Intro también. Un programa que no termina nunca se para con
**Parar**, o con Escape. Cuando una línea tiene un error, las palabras de
debajo de la pantalla dicen qué línea es, y el editor la marca.

La mitad derecha es la guía, un capítulo cada vez, con **Atrás**,
**Siguiente** y la lista de **Capítulos**. El niño lee allí un programa y
lo escribe en el editor. El botón de debajo de cada programa lo escribe
por él, salvo que un adulto haya apagado *Escríbemelo* para ese niño en
los **Ajustes** de BASIC del panel, para que escriba todos los programas.
Los treinta capítulos van desde un primer `PRINT` hasta el dibujo, el
color, el sonido y juegos para guardar. Cada capítulo termina con ideas
para seguir probando, y un recuadro **Para el adulto** que dice lo que
enseña el capítulo.

El programa del editor se queda allí cuando se cierra BASIC, hasta que el
niño pulsa **Nuevo**. Para conservar un programa, **Guardar** abre una
ventana con las carpetas del niño, en **Descargas**, para elegir dónde
guardarlo y con qué nombre, como un archivo `.bas`. **Abrir** abre la
misma ventana para traerlo de vuelta.

![BASIC](../images/es/module-basic.png)

Más en [su página](modules/basic.md).

### CodeCombat

**CodeCombat** es una puerta a la web de CodeCombat, donde los niños a
partir de nueve años aprenden a escribir Python y JavaScript de verdad
jugando: un héroe recorre cada nivel como le dice el programa del niño.
La web es de CodeCombat, en el idioma del niño, y el módulo la abre a
ella y a ninguna otra. Kidux no tiene ninguna relación con CodeCombat.

Necesita internet y una cuenta de CodeCombat. Los primeros niveles son
gratis. Casi toda la web necesita una suscripción, que un adulto compra
desde otro ordenador, porque el módulo no abre ninguna otra web.

Un adulto pone la cuenta de cada niño en los **Ajustes** de CodeCombat
del panel: su correo y su contraseña. Entonces el módulo entra solo cada
vez que se abre, diciendo *Conectándose a CodeCombat…* mientras tanto.
Pone la web en el idioma del niño y abre donde se empieza a jugar. El
niño nunca ve la contraseña. Si la cuenta no es correcta o la web no
contesta, el módulo lo dice y ofrece intentarlo otra vez.

Sin cuenta puesta, el módulo dice que lo más fácil es que un adulto la
ponga en el panel, y ofrece un botón para entrar a mano mientras tanto.
Ese botón abre la ventana de entrada de la web, donde el niño escribe el
correo y la contraseña de la cuenta. Entrar con Google, Facebook o Clever
no lleva a ninguna parte aquí. La web puede preguntar por sus cookies la
primera vez; esa pregunta es de la propia web.

![CodeCombat](../images/es/module-codecombat.png)

Más en [su página](modules/codecombat.md).

### Wikipedia

**Wikipedia** es una puerta a la enciclopedia entera, en el idioma del
niño, y a los proyectos que enlaza, como Wikcionario y Wikilibros. Es la
Wikipedia que lee todo el mundo, escrita para todos y no solo para niños,
así que un adulto decide si un niño la lee, a partir de los ocho años. Un
enlace que salga de Wikipedia y sus proyectos no lleva a ninguna parte.

Una barra arriba de la ventana tiene **Atrás** y **Adelante**, que van a
la página anterior y a la siguiente. Se ven apagados cuando no hay adónde
ir. **Alt+Izquierda**, y el botón de volver de un ratón que lo tenga,
también vuelven. Wikipedia necesita internet siempre que se usa.

![Wikipedia](../images/es/module-wikipedia.png)

Más en [su página](modules/wikipedia.md).

### Correo

**Correo** es un buzón de correo propio del niño, en Thunderbird, el
programa de correo, para niños desde los ocho años. El niño lee y escribe
allí sus mensajes, y no tiene nada que configurar: la cuenta es la que da
un adulto. Sirve con Gmail, Outlook, iCloud y cualquier otro proveedor
que hable IMAP. Necesita internet para enviar y recibir.

Un adulto pone la cuenta en los **Ajustes** de Correo del panel: la
**Dirección de correo** del niño, y el **Nombre** con el que salen sus
mensajes. Correo encuentra por sí solo los servidores del proveedor para
Gmail, Outlook, Hotmail, iCloud, Yahoo y casi todos los demás. Para un
proveedor que no encuentra, **Servidor de entrada** y **Servidor de
salida** llevan los servidores IMAP y SMTP del proveedor, tal como él los
da, como `imap.example.org`. Un servidor en un puerto propio se escribe
con el puerto, como `imap.example.org:143`.

Después, el adulto abre Correo con el niño la primera vez. Con una cuenta
de Gmail o de Outlook, se abre dentro de Correo la ventana de entrada de
Google o de Microsoft. El adulto entra allí, con el segundo paso si la
cuenta lo tiene, y Correo se queda dentro. Con cualquier otro proveedor,
Correo pide la contraseña una vez. El adulto la escribe, con la casilla
de recordarla marcada, y Correo la guarda. La contraseña se queda en la
parte del ordenador que es solo del niño, que nadie más en él puede
leer. El panel no la tiene nunca.

La cuenta de Google de un niño menor de trece años se gestiona con Family
Link, y Google no deja que una cuenta así entre en Correo. Para ella está
el módulo **Gmail**.

Lo que el niño cambie en la cuenta vuelve a estar como era la próxima vez
que se abre Correo, y una cuenta añadida a mano desaparece: la cuenta es
siempre la que se dio en el panel. Sin una dirección en el panel, o con
un proveedor que Correo no encuentra y sin servidores puestos, Correo se
abre solo con sus carpetas locales.

Un enlace en un mensaje no lleva a ninguna parte. Un adjunto se guarda en
las **Descargas** del niño, y nunca se abre con otro programa. El chat de
Correo, sus complementos y sus ajustes avanzados están cerrados. Cuando
un servidor no contesta, Correo lo dice en una burbuja encima de la
barra, y en la línea de su parte de abajo.

![Correo](../images/es/module-mail.png)

Más en [su página](modules/mail.md).

### Gmail

**Gmail** es una puerta a la web de Gmail, para un niño con una cuenta de
Google, desde los ocho años. Es Gmail tal como es en cualquier ordenador,
en el idioma del niño, y el módulo la abre a ella y a ninguna otra web:
un enlace que salga de ella no lleva a ninguna parte. Es el módulo para
un niño menor de trece años, cuya cuenta de Google se gestiona con Family
Link y no puede entrar en **Correo**. Sirve con cualquier cuenta de
Google, para una familia que prefiera la web. Kidux no tiene ninguna
relación con Google. Necesita internet siempre que se usa.

Un adulto pone la cuenta de Google del niño en los **Ajustes** de Gmail
del panel, como su **Dirección de correo**. La página de entrada de
Google se abre entonces con la dirección ya escrita. El adulto abre Gmail
con el niño la primera vez y entra allí, con la contraseña y, si Google
lo pide, el segundo paso. Gmail se queda dentro después. Cerrarlo, salir
de la sesión o apagar el ordenador no cierra la sesión del niño, y Google
vuelve a preguntar solo cuando él lo decide. La contraseña se escribe
solo en la página de Google; el panel no la tiene nunca. La web puede
preguntar por sus cookies la primera vez; esa pregunta es de Google.

![Gmail](../images/es/module-gmail.png)

Más en [su página](modules/gmail.md).

### Kig

**Kig** es geometría que el niño puede mover. Los puntos, las rectas, las
circunferencias y las figuras se ponen sobre el lienzo, y cada una
conserva su regla cuando el niño arrastra aquello de lo que se construyó:
el punto medio sigue en medio, y la paralela sigue paralela. Es para
niños de diez a catorce años, en el idioma del niño, y funciona sin
internet. Lo que el niño dibuja se puede guardar como un archivo en sus
carpetas. Viene con una guía de seis lecciones.

![Kig](../images/es/module-kig.png)

Más en [su página](modules/kig.md).

### Kalzium

**Kalzium** es la tabla periódica. Cada elemento se abre con cómo es,
dónde se encontró, una foto y un dibujo de su átomo. Un deslizador enseña
qué elementos son sólidos, líquidos o gases a cada temperatura, y hay un
glosario de las palabras. Es para niños de diez años en adelante, en el
idioma del niño, y funciona sin internet. Viene con una guía de tres
lecciones.

![Kalzium](../images/es/module-kalzium.png)

Más en [su página](modules/kalzium.md).

### Step

**Step** es un laboratorio de física. El niño pone cuerpos, muelles,
cuerdas y fuerzas sobre el plano, le da a reproducir y mira qué pasa, con
medidores y gráficas para leerlo. Los ejemplos de su menú Archivo son
experimentos listos para correr. Es para niños de diez años en adelante,
en el idioma del niño, y funciona sin internet. Su menú para descargar
más experimentos está apagado. Un experimento se puede guardar como un
archivo en las carpetas del niño. Viene con una guía de seis lecciones.

![Step](../images/es/module-step.png)

Más en [su página](modules/step.md).

### Simulaciones

**Simulaciones** son experimentos para jugar en la pantalla: formar un
número, equilibrar un balancín, doblar un rayo de luz, frotar un globo en
un jersey, construir un átomo, poner planetas en órbita. Son las
simulaciones interactivas de PhET, hechas por la Universidad de Colorado
Boulder y usadas en escuelas de todo el mundo. Kidux las ha elegido para
niños de seis a catorce años y las ha ordenado por grupo y edad, en el
idioma del niño. Están en el ordenador y funcionan sin internet. Cada una
se abre en su propio marco, con **Simulaciones** arriba para volver a la
lista. Las simulaciones son las versiones que PhET publicó bajo la
licencia Creative Commons Atribución 4.0. Kidux no tiene relación con
PhET.

![Simulaciones](../images/es/module-simulations.png)

![Una simulación abierta](../images/es/module-simulations-open.png)

Más en [su página](modules/simulations.md).

### Fotografía

**Fotografía** es una guía para hacer fotos con una cámara de verdad, para
niños de ocho a doce años que ya leen bien, en el idioma del niño. No
necesita nada de internet, pero necesita una cámara: cualquiera que tenga
un dial o un menú para sus modos, sea una compacta, una bridge o una
réflex, y para empezar incluso un móvil. El ejemplo de la guía es la
Olympus XZ-2. El recuadro **En la Olympus XZ-2** de cada capítulo dice qué
botón, dial o menú hace lo que enseña el capítulo, y que otras cámaras
tienen lo mismo con otros nombres.

Los treinta capítulos empiezan por una caja oscura con un agujero, que es
lo que sigue siendo toda cámara. Siguen con el objetivo, el obturador, el
diafragma y el ISO; los modos de la cámara, y por qué el manual es el más
fiable con una luz que no cambia; cómo mide la luz la cámara y dónde
enfoca; la profundidad de campo, las fotos de cerca y el zoom. Después
vienen la composición, la luz, el color y las personas. Los últimos
capítulos son sobre mirar las fotos y elegirlas. Cada capítulo tiene fotos
de su efecto, dibujos de lo que enseña la pantalla de la cámara, un
**Pruébalo** para hacer con la cámara ese día, e ideas para seguir
probando. Un recuadro **Para el adulto** dice qué enseña el capítulo y en
qué ayudar: una habitación a oscuras, una linterna, el flash, una calle al
anochecer.

**Atrás**, **Siguiente** y la lista de **Capítulos** recorren la guía.
Casi todas las fotos son fotos libres de otras personas, cada una con su
autor debajo. Donde ninguna enseñaba un efecto con claridad, lo enseña una
imagen hecha por un ordenador, y lo dice debajo.

![Fotografía](../images/es/module-photography.png)

Más en [su página](modules/photography.md).

## 10. Actualizar y reinstalar

Las actualizaciones se instalan solas, cada mañana y en segundo plano.
Incluyen tanto las actualizaciones de seguridad de Debian como las de
Kidux, y no hay que hacer nada para recibirlas. Mientras un niño está
dentro de su sesión, las actualizaciones esperan, y se instalan cuando ha
salido el último, de modo que nada de lo que esté usando cambia mientras
tanto. Si un niño intenta entrar justo mientras se están instalando, la
pantalla le avisa de que el ordenador se está actualizando, y puede entrar
un momento después.

Las actualizaciones de Kidux vienen de `apt.kidux.org`, un servidor del
proyecto. Como cualquier servidor web, anota cada petición con la
dirección de la que llega, y esas anotaciones dicen al proyecto cuántos
ordenadores usan Kidux y qué módulos instalan. La petición dice que viene
de un ordenador con Kidux y nada más: ni nombre, ni versión, ni nada de
ningún niño. **Compartir estadísticas de uso**, en la página Sistema, en
Avanzado, añade un identificador hecho solo para este ordenador, para que se cuente
como un ordenador y no como una dirección; está encendido salvo que lo
apagues tú.

Si quieres instalarlas en el momento, sin esperar a la mañana siguiente,
usa la página **Sistema** del panel de adulto:

1. Pulsa **Buscar actualizaciones**. La página dice cuántas
   actualizaciones hay, y cuáles.
2. Pulsa **Instalar**. Una barra muestra cuánto falta.
3. Si una actualización necesita reiniciar el ordenador, la página lo
   dice, con **Reiniciar ahora**.

Las actualizaciones solo se instalan cuando no hay ningún niño dentro de
su sesión, para que nada de lo que esté usando cambie mientras tanto. Si
hay alguno, la página lo dice.

![Actualizaciones encontradas, en el panel de adulto](../images/es/panel-updates-found.png)

![Actualizaciones instaladas](../images/es/panel-updates-done.png)

## 11. Si algo va mal

### Kidux no arranca

El ordenador conserva la forma de arrancar de Debian detrás de la
contraseña de recuperación, la que muestra la página **Sistema** del
panel de adulto.

1. Enciende el ordenador y pulsa Escape una o dos veces durante el primer
   segundo, antes de que aparezca el logo. Aparece un menú.
2. El menú pide un nombre de usuario y una contraseña. El usuario es
   `kidux`. La contraseña es la de recuperación.
3. Elige la primera entrada de Debian.

El ordenador arranca como un Debian normal, sin las pantallas de Kidux.
Alguien que conozca Debian puede entonces ver qué ha pasado.

### Un administrador necesita una consola de texto

Kidux desactiva las consolas de texto, porque una pantalla de inicio de
sesión en el ordenador de un niño es una puerta. Para recuperar una y
hacer una reparación:

1. Llega al menú como arriba.
2. Pulsa `e` sobre la entrada **Kidux**.
3. Añade `kidux.console` al final de la línea que empieza por `linux`.
4. Pulsa F10.

Las consolas vuelven solo para ese arranque.

### El ordenador no se duerme, o no se apaga guardando

Un administrador con una consola de texto (arriba), o por SSH, puede ver
qué puede hacer el ordenador y qué hizo:

```sh
busctl call org.freedesktop.login1 /org/freedesktop/login1 \
    org.freedesktop.login1.Manager CanSuspendThenHibernate
cat /sys/kernel/security/lockdown     # todo lo que no sea [none] es Secure Boot
swapon --show                         # un swap en el disco, no zram
systemd-analyze cat-config systemd/logind.conf | grep -i lid
cat /etc/systemd/sleep.conf.d/50-kidux-power.conf
systemd-inhibit --list                # qué lo mantiene despierto
journalctl -b -1 | grep -i -e hibernat -e suspend
```

`yes` en la primera quiere decir que puede dormir y después apagar
guardando. El ajuste de la tapa está en
`/etc/systemd/logind.conf.d/50-kidux-power.conf`, que escribe el panel;
un fichero allí o en `/usr/lib/systemd/logind.conf.d/` cuyo nombre vaya
detrás en orden alfabético y fije `HandleLidSwitch` manda sobre él, y hay
que quitarlo. `sudo systemctl hibernate` prueba a apagar guardando al
momento.

### Quitar Kidux de un ordenador

Desinstala el paquete `kidux-session` y reinicia. El ordenador vuelve a
ser un Debian normal. Las cuentas de los niños, sus archivos y todos los
ajustes se conservan, así que Kidux se puede volver a poner más tarde
exactamente como estaba.

## 12. Dónde pedir ayuda

Abre una incidencia en la página del proyecto en GitHub, en español o en
inglés.
