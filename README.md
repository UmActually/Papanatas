# Papanatas    

### El bot oficial de mi server de Discord (Sociedad de Patanes)    

By Leonardo - UmActually

`Papanatas Autómata Multiparadigma IV` inició como un hobby muy informal en preparatoria, y terminó siendo uno de los proyectos que más ha aportado a mis conocimientos de programación. En este repositorio podráis encontrar una a veces elegante y otras veces muy descarada amalgama de código, cultivada a lo largo de dos años de aprender Python de forma autodidacta.     

Este bot está construido con la librería de [pycord](https://github.com/Pycord-Development/pycord), y en su tiempo, [discord.py](https://github.com/Rapptz/discord.py). Estas librerías ahorran el problema de tratar con la API de Discord, que se basa no solo en HTTP sino también en WebSocket. Y lo empaquetan todo en un inmenso y surreal sistema de clases y objetos. Recomiendo echarle un vistazo al source code de estos paquetes.    

## Funciones

Para la lista completa de comandos y su descripción, véase [todos los comandos](#todos-los-comandos).

### Música

Papanatas es un **full-fledged music bot**. No estoy enterado del mundo de los bots de música serios del momento, pero sé que, comparado con lo que fueron bots como Rythm, Hydra y FredBoat, Papanatas sí les daba unos tiros. Para poner una canción, basta con el comando `/p`.    

![Ejemplo del player de música](https://cdn.discordapp.com/attachments/765560541309304862/1060354393783931040/example.jpg)    

Con este comando es posible tanto realizar búsquedas como pasar directamente el enlace de **[YouTube](https://github.com/ytdl-org/youtube-dl)** o **[Spotify](https://github.com/UmActually/spotifyatlas)**. Si está una canción sonando ya, el uso de `/p` solamente agregará canciones a la cola. Asimismo, si se pasa como query un enlace de **Spotify** se agregará a la cola una selección de **10 pistas** al azar como máximo, en el caso de ser una playlist, un álbum o un artista.

Recientemente agregué los comandos `/playlist`, `/album` y `/artist`. Estos comandos hacen una **búsqueda en Spotify** y agregan a la cola las canciones del top result que arroje. Igual que al usar `/p` con el link de un artista, el comando `/artist` pone las **diez canciones top**. 

![Ejemplo de búsqueda de artista](https://cdn.discordapp.com/attachments/765560541309304862/1065470313778909195/example.jpg)

Para búsquedas específicas en **YouTube**, también se puede usar `/ly` y `/ost`, que agregan `" lyrics"` y `" ost"` respectivamente a tu búsqueda. Por ejemplo, si bien `/p otherside` pone la de **Red Hot Chili Peppers**, `/ost otherside` va a regresar la de **Lena Raine**. También, estos comandos pueden **reemplazar** la canción que esté sonando si no escribes nada para buscar. Así, en el momento en que te salga un Official Video donde nomás no quiere empezar la música, puedes mandar `/ly` y la canción se volverá a buscar con el sufijo `" lyrics"`.

Para **alterar la cola** de canciones están también los comandos `/skip`, `/shuffle`, y `/clear`.    

Por último, Papanatas también tiene un **soundboard**, para aquellos individuos obsesionados con ponerle banda sonora a su vida. Revisa `/soundboard` para más detalles.    

### Juegos    

Papanatas ofrece un catálogo de nada más y nada menos que dos juegos: **UNO** y **ajedrez** (este último está en progreso tho). Para jugar juegos, el server debe tener cierto setup en sus canales. Puedes iniciar partidas con `/uno` y `/chess` respectivamente.    

En UNO el jugador puede seleccionar su carta enviando un mensaje en su canal con el número de **posición** de dicha carta. Véase la sección de [cómo jugar UNO](#para-jugar-uno) para más detalles.    

![Ejemplo de partida de UNO](https://cdn.discordapp.com/attachments/765560541309304862/1060640673499463762/example.jpg)    

El ajedrez se controla de forma parecida, ingresando las **coordenadas** de la pieza y las coordenadas de destino en el mensaje. Realmente no se me ocurre de otra. Este juego sigue bastante rudimentario: apenas y revisa movimientos legales.    

![Ejemplo de partida de ajedrez](https://cdn.discordapp.com/attachments/765560541309304862/1060651267665440798/example.jpg)    

### NLP    

Algunos comandos de Papanatas tienen una implementación con **natural language processing**. Cuando un mensaje inicia con `natas` se interpretará el lenguaje natural buscando mediante patrones el comando que más le corresponda. Con la ayuda de [@Dan](https://github.com/Noe-Sanchez) logramos incorporar la pipeline de NLP de [Spacy](https://spacy.io/) con un modelo del lenguaje español. Revisa `/natas` para más detalles.    

![Ejemplo de comandos con NLP](https://cdn.discordapp.com/attachments/765560541309304862/1060708292122386463/example.jpg)    

Cabe notar que nuestro sistema de búsqueda de comandos puede mejorar. Está más hard-coded de lo que quisiéramos.    

### Manipulación de imágenes  

Papanatas también puede **agregar texto a imágenes** usando [Pillow](https://python-pillow.org/). El comando `/meme` toma la imagen más reciente del canal y le agrega el texto que le digas. Es posible especificar el color, contorno, posición y font del texto. El bot también puede buscar en los mensajes patrones alusivos a algunos memes comunes y enviar el meme correspondiente con el texto del mensaje.  
  
![Ejemplo de meme](https://cdn.discordapp.com/attachments/765560541309304862/1061046393826967612/example.jpg)  

### Otras funciones  

- También se pueden crear **encuestas** con `/poll`. Primero se ingresa el título y luego las opciones separadas por `;`. Llevará la cuenta de los votos mientras el bot siga corriendo.  
- Papanatas saca a todos los usuarios de un voice chat si solo quedan bots.  
- Papanatas tiene gustos muy interesantes. Cada 10 minutos cambiará su **Activity** en su perfil.   
- Puedes convertir coordenadas de Overworld a **Nether** con `/coords`.  
- Para enviar y alterar mensajes puedes usar `/echo`, `/tell`, y `/salt`.  

> La mayor parte de las features de Papanatas han sido retiradas del código, ya sea por perder utilidad (muchas estaban relacionadas a los estudios y a mis amigos de prepa, shoutout, los extraño) o simple y sencillamente porque presentaban un humor muy audaz.    
  
## Apéndice    

### Todos los comandos  

| Comando                                               | Descripción                                                                                                                         |
|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `/info`                                               | Información de Papanatas.                                                                                                           |
| `/time`                                               | Fecha y hora en México.                                                                                                             |
| `/natas`                                              | Información y ejemplos de 'natas Natural Language.                                                                                  |
| `/dl [link_or_search]`                                | Descargar un video DE DURACIÓN RAZONABLE con YouTube DL.                                                                            |
| `/act [type?] [name?] [status?]`                      | Cambiar el status del perfil de Papanatas.                                                                                          |
| `/nk [member] [nick]`                                 | Cambiar el nick de cualquier usuario.                                                                                               |
| `/hr`                                                 | Horario de clases de prepa. Este comando obviamente ya no nos sirve. Solo está aquí por nostalgia.                                  |
| `/coords [xyz]`                                       | Traduce coordenadas de minecraft de Overworld a Nether.                                                                             |
| `/uno`                                                | Iniciar nuevo juego de UNO.                                                                                                         |
| `/chess`                                              | Iniciar nuevo juego de ajedrez.                                                                                                     |
| `/echo [text]`                                        | Enviar un mensaje en este canal.                                                                                                    |
| `/tell [channel] [text]`                              | Enviar un mensaje a otro canal.                                                                                                     |
| `/reply [message_id] [text] [channel?]`               | Responder a un mensaje.                                                                                                             |
| `/edit [message_id] [text] [channel?]`                | Editar un mensaje de Papanatas.                                                                                                     |
| `/salt [seconds] [text]`                              | Enviar un mensaje que se autodestruirá en la cantidad de segundos especificada.                                                     |
| `/brazil [member]`                                    | Mandar a alguien a Brasil.                                                                                                          |
| `/argentina`                                          | Sacar a todos de Brasil.                                                                                                            |
| `/jn`                                                 | Unirse al voice.                                                                                                                    |
| `/lv`                                                 | Salirse del voice.                                                                                                                  |
| `/p [query]`                                          | Agregar una canción a la fila.                                                                                                      |
| `/skip`                                               | Siguiente canción en la fila.                                                                                                       |
| `/undo`                                               | Quitar la última canción de la fila (que tú hayas agregado).                                                                        |
| `/clear`                                              | Borrar todas las rolas de la fila.                                                                                                  |
| `/shuffle`                                            | Shufflear la fila.                                                                                                                  |
| `/playlist [query]`                                   | Agregar una playlist a la fila, guardada en el canal de \#playlists. En caso de no haber match, realiza una búsqueda en Spotify.    |
| `/album [query]`                                      | Buscar un álbum en Spotify y agregar a la cola las canciones del top result.                                                        |
| `/artist [query]`                                     | Buscar un artista en Spotify y agregar a la cola las (top 10) canciones del top result.                                             |
| `/ly [query?]`                                        | Poner una canción agregando "lyrics" en la búsqueda. Si no se teclea búsqueda, reemplazar lo que está sonando agregándole "lyrics". |
| `/ost [query?]`                                       | Mismo funcionamiento que `/ly`, pero agregando "ost".                                                                               |
| `/soundboard`                                         | Mostrar todos los efectos del soundboard.                                                                                           |
| `/poll [title] [options]`                             | Crear nueva encuesta. Separa las opciones con ";"                                                                                   |
| `/meme [text] [position?] [color?] [font?] [stroke?]` | Crear un meme con la imagen más reciente del canal. Si la posición es "top & bottom", separar el texto de arriba y abajo con ";".   |
| `/skipper [text]`                                     | Meme de "Goku le gana".                                                                                                             |
| `/able [text]`                                        | Meme de la bola amarilla ansiosa.                                                                                                   |
| `/yoda [text]`                                        | Meme de "Mucho texto".                                                                                                              |
| `/jimmy [text]`                                       | Meme de Jimmy Neutrón explicándote algo.                                                                                            |
| `/chtm [text]`                                        | Meme de la bola amarilla sacando el dedo.                                                                                           |

### Para jugar UNO    

1. Presiona el link del canal que te toque. Es un canal privado.     
   - Papanatas te va a decir los turnos y el número de cartas de cada quien. La carta de arriba es la del centro. Tus cartas son las de abajo.    
2. Si es tu turno, selecciona tu carta escribiendo el número de la POSICIÓN de la carta.    
   - Si es un +4 o un Wild, debes especificar el nuevo color además de tu elección de carta. Ej: `4 azul`.    
   - Algunas cartas serán grises. Esas las puedes poner sobre cualquier color, pero van a adquirir el color de la carta que estaba antes en el centro.    
   - Puedes comer una carta escribiendo `draw`.    
   - Mis reglas. En este juego se acumulan +4's.
