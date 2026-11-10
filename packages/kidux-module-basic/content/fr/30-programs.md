---
source_sha256 = "924f12dbb27b0e22cfa96ce9b83c5f5e9eeff65f0032f2ec22d13b93fbec0ce1"
---
# Des programmes à garder

Ces programmes utilisent tout ce qu'il y a dans ce guide. Tape-les, joue
avec, change-les, et garde ceux qui te plaisent avec **Enregistrer**.

## Le jeu des réflexes

Es-tu rapide ? Appuie sur une touche dès que l'étoile apparaît.

```basic keys=x
10 RANDOMIZE
20 CLS
30 PRINT "QUAND L'ETOILE APPARAIT, APPUIE SUR UNE TOUCHE !"
40 SLEEP 1000 + INT(RND * 3000)
50 PRINT "*"
60 LET T# = TIMER
70 IF INKEY$ = "" THEN 70
80 PRINT "TU AS MIS "; INT((TIMER - T#) * 100) / 100; " SECONDES"
```

`TIMER`, c'est l'horloge de l'ordinateur : les secondes qu'il a comptées
depuis le début de 1970, avec des décimales, un nombre de dix chiffres.
C'est plus que ce que garde une boîte ordinaire : l'heure va donc dans une
boîte `#`, comme l'a montré le chapitre 17. La ligne 60 note l'heure à
laquelle l'étoile est apparue, et la ligne 80 la soustrait de l'heure à
laquelle la touche est arrivée.

## La ligue de la Banquise

Cinq équipes de pingouins jouent au basket. Une victoire vaut 2 points et
une défaite 1. Le programme calcule les points et classe les équipes, la
meilleure en premier.

```basic
10 DIM N$(5), P(5)
20 FOR I = 1 TO 5
30 READ N$(I), W, L
40 LET P(I) = W * 2 + L
50 NEXT I
60 FOR R = 1 TO 4
70 FOR I = 1 TO 5 - R
80 IF P(I) < P(I + 1) THEN SWAP P(I), P(I + 1): SWAP N$(I), N$(I + 1)
90 NEXT I
100 NEXT R
110 PRINT "LA LIGUE DE LA BANQUISE"
120 FOR I = 1 TO 5
130 PRINT I; ". "; N$(I); SPACE$(10 - LEN(N$(I))); P(I); " POINTS"
140 NEXT I
150 DATA PIP, 6, 2, TOM, 3, 5, LULU, 7, 1, BEA, 4, 4, MAX, 2, 6
```

Quand deux étagères vont ensemble, un nom et ses points, il faut les
échanger ensemble, comme le fait la ligne 80. `SPACE$(10 - LEN(N$(I)))`
écrit des espaces après chaque nom pour que les points soient alignés.

## Le carnet d'adresses

```basic keys=LULU,Enter,SAM,Enter,Enter
10 DIM N$(4), T$(4)
20 FOR I = 1 TO 4: READ N$(I), T$(I): NEXT I
30 INPUT "LE NUMERO DE QUI ? (ENTREE POUR ARRETER) "; W$
40 IF W$ = "" THEN END
50 FOR I = 1 TO 4
60 IF N$(I) = W$ THEN PRINT W$; " : "; T$(I): GOTO 30
70 NEXT I
80 PRINT "PAS DANS LE CARNET"
90 GOTO 30
100 DATA PIP, 01 99 00 01 01, TOM, 01 99 00 01 02
110 DATA LULU, 01 99 00 01 03, BEA, 01 99 00 01 04
```

Appuyer sur Entrée sans rien taper donne une réponse vide, et la ligne 40
termine le programme.

## Une liste dans l'ordre alphabétique

Tape des prénoms dans n'importe quel ordre, et l'ordinateur les met dans
l'ordre de l'alphabet. Une réponse vide veut dire qu'il n'y en a plus.

```basic keys=TOM,Enter,ANA,Enter,PIP,Enter,BEA,Enter,Enter
10 DIM N$(20)
20 LET C = 0
30 INPUT "UN PRENOM (ENTREE POUR FINIR) ? "; A$
40 IF A$ = "" OR C = 20 THEN 70
50 LET C = C + 1: LET N$(C) = A$
60 GOTO 30
70 FOR R = 1 TO C - 1
80 FOR I = 1 TO C - R
90 IF N$(I) > N$(I + 1) THEN SWAP N$(I), N$(I + 1)
100 NEXT I
110 NEXT R
120 FOR I = 1 TO C: PRINT N$(I): NEXT I
```

## Ta bibliothèque

Note tes propres livres dans les lignes `DATA` : le titre, puis qui l'a
écrit. Le programme trouve tous les livres d'un auteur.

```basic keys=ROSA,Enter
10 INPUT "QUEL AUTEUR ? "; A$
20 LET F = 0
30 READ T$, W$
40 IF T$ = "FIN" THEN 70
50 IF W$ = A$ THEN PRINT T$: LET F = F + 1
60 GOTO 30
70 PRINT F; " LIVRES DE "; A$
80 DATA LE CHATEAU DE NEIGE, ROSA
90 DATA DU POISSON POUR LE GOUTER, MAX
100 DATA LE PINGOUIN DE LA NUIT, ROSA
110 DATA FIN, FIN
```

## Le jeu de dessin

Dessine avec les flèches ; la barre d'espace change la couleur. Échap
arrête le programme, et le dessin reste à l'écran.

```basic keys=Right,Right,Space,Down,Down forever
10 SCREEN 12
20 LET X = 320: LET Y = 240: LET C = 14
30 LET K$ = INKEY$
40 IF K$ = "" THEN 30
50 IF K$ = " " THEN LET C = C + 1: IF C > 15 THEN LET C = 1
60 IF LEN(K$) < 2 THEN 30
70 LET OX = X: LET OY = Y
80 LET A$ = RIGHT$(K$, 1)
90 IF A$ = "H" THEN LET Y = Y - 8
100 IF A$ = "P" THEN LET Y = Y + 8
110 IF A$ = "K" THEN LET X = X - 8
120 IF A$ = "M" THEN LET X = X + 8
130 LINE (OX, OY)-(X, Y), C
140 GOTO 30
```

Une flèche, ce sont deux caractères : `CHR$(0)` et une lettre, `H` vers le
haut, `P` vers le bas, `K` vers la gauche et `M` vers la droite. La ligne
60 ne laisse passer que ces touches-là, et la ligne 80 regarde la lettre.

## Bien programmer

Tu sais maintenant écrire des programmes. Voici les habitudes qui les
rendent bons :

- **Réfléchis d'abord.** Que doit faire le programme ? Que demande-t-il,
  et que montre-t-il ?
- **Dessine l'organigramme** avant d'écrire, comme au chapitre 13.
- **Donne de bons noms aux boîtes** : `SCORE` en dit plus que `S`.
- **Mets des `REM`** là où commence une partie du programme, pour dire à
  quoi elle sert.
- **Attrape les mauvaises réponses**, pour qu'une faute de frappe n'arrête
  pas le programme, comme au chapitre 22.
- **Fais un menu** quand le programme fait plusieurs choses, comme au
  chapitre 23.
- **Essaie-le avec quelqu'un d'autre.** Il fera des choses auxquelles tu
  n'aurais jamais pensé.

> [cheer] C'est tout le guide. À partir d'ici, les programmes sont à toi.

::: adult
Le guide s'arrête là où un enfant peut continuer seul : changer ces
programmes est la meilleure suite, et les habitudes de la dernière partie
sont les mêmes dans tous les langages qu'il rencontrera ensuite, Scratch,
Python ou n'importe quel autre.
:::
