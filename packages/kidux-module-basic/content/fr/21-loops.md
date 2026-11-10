---
source_sha256 = "f73c91e9649d41b8fbdc18a4bd68d9ba0c76dae6725059c3363670cc82b17347"
---
# FOR et NEXT, plus loin

## Sortir d'une boucle plus tôt

Une boucle `FOR` compte jusqu'au bout, mais un `GOTO` peut en sortir
avant. Celle-ci met des nombres au carré jusqu'à ce que tu tapes 0, ou
jusqu'à ce qu'elle en ait fait dix :

```basic keys=3,Enter,12,Enter,0,Enter
10 FOR N = 1 TO 10
20 INPUT "UN NOMBRE, OU 0 POUR ARRETER ? "; X
30 IF X = 0 THEN 60
40 PRINT X; " FOIS "; X; " FONT "; X * X
50 NEXT N
60 PRINT "SALUT !"
```

## Une boucle qui attend

`SLEEP` fait attendre l'ordinateur. Le nombre qui le suit est en
millièmes de seconde : `SLEEP 1000` attend donc une seconde.

```basic
10 FOR N = 5 TO 1 STEP -1
20 PRINT N
30 SLEEP 1000
40 NEXT N
50 PRINT "DECOLLAGE !"
```

> [point] `SLEEP 500` attend une demi-seconde, et `SLEEP 3000` trois
> secondes.

## Des boucles dans des boucles

Une boucle peut avoir une autre boucle à l'intérieur. Celle de l'intérieur
fait tout son tour chaque fois que celle de l'extérieur fait un tour,
comme les minutes à l'intérieur des heures d'une horloge.

```basic
10 FOR R = 1 TO 4
20 FOR S = 1 TO R
30 PRINT "*";
40 NEXT S
50 PRINT
60 NEXT R
```

La boucle de l'intérieur doit finir avant celle de l'extérieur :
`NEXT S` vient avant `NEXT R`.

## Les tables, une par une

```basic
10 FOR T = 2 TO 5
20 CLS
30 PRINT "LA TABLE DE "; T
40 FOR N = 1 TO 10
50 PRINT T; " X "; N; " = "; T * N
60 NEXT N
70 SLEEP 3000
80 NEXT T
```

Chaque table reste trois secondes à l'écran, puis la suivante prend sa
place.

## Continue d'essayer

- Transforme le triangle d'étoiles en sapin, avec un tronc en bas.
- Fais attendre les tables cinq secondes, ou va de la table de 2 à la
  table de 10.

::: adult
Sortir d'une boucle avec `GOTO` est la façon dont le faisaient les
ordinateurs familiaux, et cela fonctionne ici. Les boucles imbriquées sont
la première vraie difficulté pour beaucoup d'enfants : dessiner les
étoiles sur du papier quadrillé, rangée par rangée, aide.
:::
