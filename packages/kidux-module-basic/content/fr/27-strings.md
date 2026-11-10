---
source_sha256 = "937a86dbadf882448559f2ef4c7879ba2cdbdc937da4fdd9f09604e429d643d3"
---
# Les chaînes de caractères

Une boîte à mots contient une **chaîne de caractères** : des lettres l'une
après l'autre, comme des perles sur un fil. BASIC a des outils pour
démonter les chaînes.

- `LEN(W$)`, c'est le nombre de lettres de W$.
- `LEFT$(W$, 3)`, ce sont ses 3 premières lettres, et `RIGHT$(W$, 3)` ses
  3 dernières.
- `MID$(W$, 2, 4)`, ce sont 4 lettres à partir de la deuxième.

```basic
10 LET W$ = "BONHOMME"
20 PRINT LEN(W$)
30 PRINT LEFT$(W$, 3)
40 PRINT RIGHT$(W$, 5)
50 PRINT MID$(W$, 4, 3)
```

## Lettre par lettre

```basic keys=PINGOUIN,Enter
10 INPUT "UN MOT ? "; W$
20 FOR I = 1 TO LEN(W$)
30 PRINT MID$(W$, I, 1)
40 NEXT I
```

Et à l'envers, pour voir ton mot dans un miroir :

```basic keys=NOEL,Enter
10 INPUT "UN MOT ? "; W$
20 LET B$ = ""
30 FOR I = LEN(W$) TO 1 STEP -1
40 LET B$ = B$ + MID$(W$, I, 1)
50 NEXT I
60 PRINT B$
```

## Nombres et chaînes

`VAL` transforme une chaîne de chiffres en nombre, et `STR$` transforme un
nombre en chaîne :

```basic
10 LET A$ = "12"
20 PRINT A$ + A$
30 PRINT VAL(A$) + VAL(A$)
40 PRINT "LA REPONSE EST" + STR$(6 * 7)
```

`"12" + "12"` colle deux chaînes ; `VAL` en fait des nombres pour les
additionner.

## Attendre une touche

`INKEY$`, c'est la touche sur laquelle on appuie, ou une chaîne vide
quand il n'y en a pas. Il n'attend pas : un programme qui veut une touche
redemande encore et encore jusqu'à ce qu'il y en ait une.

```basic keys=x
10 PRINT "APPUIE SUR UNE TOUCHE POUR REVEILLER LE PINGOUIN"
20 LET K$ = INKEY$
30 IF K$ = "" THEN 20
40 PRINT "AAAH... TU AS APPUYE SUR "; K$
```

> [point] La ligne 30 renvoie à la ligne 20 tant qu'aucune touche n'a été
> pressée. Cette petite boucle, c'est la façon dont un programme attend.

## Continue d'essayer

- Demande un prénom, et écris sa première lettre et sa longueur.
- Un mot est-il le même à l'envers ? Écris si c'est un *palindrome*, comme
  `KAYAK`.
- Fais attendre une touche au quiz du chapitre 19 après chaque réponse.

::: adult
`INKEY$` répond tout de suite : un jeu peut donc continuer à bouger
pendant qu'il surveille le clavier, comme le jeu de dessin du chapitre 30.
`STR$` met une espace devant un nombre positif, à la place de son signe.
:::
