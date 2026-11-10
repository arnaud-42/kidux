---
source_sha256 = "01c4373aecec49322b8ff1db2a73b8325218cc07300db0d71c15c7f853467e0b"
---
# Dessin, couleur et son

`SCREEN 12` transforme l'écran en une grille de points, 640 en largeur et
480 en hauteur. Un point se désigne par deux nombres entre parenthèses : à
quelle distance il est **vers la droite**, puis **vers le bas**. `(0, 0)`
est le coin en haut à gauche, et `(320, 240)` le milieu.

![L'écran comme une grille de points](screen.svg)

## Les couleurs

Chaque couleur a un numéro de 0 à 15 :

```basic
10 SCREEN 12
20 FOR C = 0 TO 15
30 LINE (C * 40, 200)-(C * 40 + 38, 280), C, BF
40 NEXT C
```

0 est le noir, 1 le bleu, 2 le vert, 3 le turquoise, 4 le rouge, 5 le
violet, 6 le marron, 7 le gris, 8 le gris foncé, puis les couleurs
claires : 9 bleu, 10 vert, 11 turquoise, 12 rouge, 13 rose, 14 jaune et 15
blanc.

## Points et lignes

- `PSET (X, Y), C` peint un point de couleur C.
- `LINE (X1, Y1)-(X2, Y2), C` trace une ligne d'un point à un autre.
- Avec `, B` à la fin, `LINE` dessine un rectangle avec ces deux coins ;
  avec `, BF`, un rectangle rempli.
- `CIRCLE (X, Y), R, C` dessine un cercle autour de (X, Y), avec R points
  du milieu jusqu'au bord.
- `PAINT (X, Y), C` remplit de la couleur C à partir de ce point jusqu'à
  ce qu'il rencontre une ligne de couleur C, comme de la peinture versée
  dans une forme.

Un ciel de nuit avec trois cents étoiles, chacune à un endroit choisi par
`RND` :

```basic
10 SCREEN 12
20 RANDOMIZE
30 FOR N = 1 TO 300
40 PSET (INT(RND * 640), INT(RND * 480)), 15
50 NEXT N
60 CIRCLE (520, 90), 50, 14
70 PAINT (520, 90), 14
```

## Une maison

```basic
10 SCREEN 12
20 LINE (0, 400)-(639, 479), 2, BF
30 LINE (200, 220)-(440, 400), 4, BF
40 LINE (200, 220)-(320, 120), 6
50 LINE (320, 120)-(440, 220), 6
60 LINE (200, 220)-(440, 220), 6
70 PAINT (320, 180), 6
80 LINE (290, 310)-(350, 400), 6, BF
90 LINE (230, 260)-(270, 300), 11, BF
100 LINE (370, 260)-(410, 300), 11, BF
110 CIRCLE (560, 70), 40, 14
120 PAINT (560, 70), 14
```

Le toit, ce sont trois lignes qui ferment un triangle, et `PAINT` le
remplit.

> [point] Dessine d'abord ton image sur du papier quadrillé, et note les
> nombres de ses coins. Ensuite, le programme est facile.

## Un bonhomme de neige

```basic
10 SCREEN 12
20 LINE (0, 0)-(639, 479), 1, BF
30 LINE (0, 420)-(639, 479), 15, BF
40 CIRCLE (320, 340), 90, 15
50 PAINT (320, 340), 15
60 CIRCLE (320, 190), 65, 15
70 PAINT (320, 190), 15
80 CIRCLE (295, 170), 8, 0
90 PAINT (295, 170), 0
100 CIRCLE (345, 170), 8, 0
110 PAINT (345, 170), 0
120 LINE (320, 192)-(365, 200), 12, BF
130 LINE (250, 120)-(390, 132), 0, BF
140 LINE (275, 60)-(365, 120), 0, BF
150 FOR B = 1 TO 3
160 CIRCLE (320, 270 + B * 40), 7, 0
170 PAINT (320, 270 + B * 40), 0
180 NEXT B
```

## Un drapeau

Le drapeau de l'île aux Pingouins : une ligne d'un coin à l'autre le coupe
en deux, et `PAINT` remplit chaque moitié. Son deuxième nombre dit où
s'arrêter : aux lignes blanches.

```basic
10 SCREEN 12
20 LINE (100, 40)-(110, 460), 7, BF
30 LINE (110, 60)-(530, 300), 15, B
40 LINE (110, 300)-(530, 60), 15
50 PAINT (200, 120), 12, 15
60 PAINT (440, 240), 11, 15
70 CIRCLE (320, 180), 30, 14
80 PAINT (320, 170), 14
```

## Le son

`SOUND F, D` joue une note. F dit à quelle hauteur elle est : 262, c'est
la note *do*, et plus le nombre est grand, plus la note est aiguë. D dit
combien de temps elle dure, en dix-huitièmes de seconde : 18, c'est une
seconde.

```basic
10 FOR N = 1 TO 14
20 READ F, D
30 SOUND F, D
40 NEXT N
50 DATA 262, 6, 262, 6, 392, 6, 392, 6, 440, 6, 440, 6, 392, 12
60 DATA 349, 6, 349, 6, 330, 6, 330, 6, 294, 6, 294, 6, 262, 12
```

Les notes à partir de do : 262 do, 294 ré, 330 mi, 349 fa, 392 sol, 440
la, 494 si, et 523 pour le do suivant. Reconnais-tu l'air ? C'est *Ah !
vous dirai-je, maman*.

## Une balle qui rebondit

Pour faire bouger quelque chose, dessine-le, attends un instant,
redessine-le en noir pour l'effacer, et dessine-le un peu plus loin. Quand
la balle arrive à un bord, elle fait demi-tour, avec un son.

```basic
10 SCREEN 12
20 LET X = 40: LET Y = 60: LET DX = 6: LET DY = 4
30 FOR T = 1 TO 600
40 CIRCLE (X, Y), 12, 0
50 LET X = X + DX: LET Y = Y + DY
60 IF X < 12 OR X > 627 THEN LET DX = -DX: SOUND 880, 1
70 IF Y < 12 OR Y > 467 THEN LET DY = -DY: SOUND 660, 1
80 CIRCLE (X, Y), 12, 14
90 SLEEP 20
100 NEXT T
```

> [cheer] La balle n'est jamais qu'un cercle dessiné puis effacé, cinquante
> fois par seconde. Un dessin animé, ce n'est rien d'autre.

## Continue d'essayer

- Ajoute une cheminée et une poignée de porte à la maison.
- Donne des bras au bonhomme de neige, deux lignes de couleur 6.
- Dessine le drapeau de ta propre île.
- Écris un air à toi avec `SOUND`, ou le début d'un air que tu connais.

::: adult
L'image reste à l'écran quand le programme se termine, et *Arrêter* la
garde aussi. `PAINT` remplit jusqu'aux lignes de la couleur donnée, ou de
la deuxième couleur quand il y en a une ; une forme dont le contour a un
trou laisse la peinture se répandre sur tout l'écran, ce que les enfants
découvrent vite.
:::
