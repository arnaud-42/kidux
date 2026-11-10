---
source_sha256 = "24c9c5cc9d61d85801d4ac1375e89da62e397522c1f920f0a490c73b370ac2d4"
---
# CHR$ et ASC : les numéros des lettres

Dans l'ordinateur, chaque lettre est un nombre. `ASC` te dit le numéro
d'une lettre, et `CHR$` retransforme un numéro en sa lettre :

```basic
10 PRINT ASC("A"), ASC("B"), ASC("Z")
20 PRINT CHR$(83); CHR$(65); CHR$(76); CHR$(85); CHR$(84); CHR$(33)
```

`A` vaut 65, `B` vaut 66, et ainsi de suite jusqu'à `Z`, 90. Une espace
vaut 32.

## L'alphabet

```basic
10 FOR C = 65 TO 90
20 PRINT CHR$(C); " ";
30 NEXT C
40 PRINT
```

## Un code secret

Pour écrire en code, remplace chaque lettre par la suivante : A devient B,
B devient C, et Z revient à A. Ton ami remplace chaque lettre par la
précédente pour lire le message.

![Chaque lettre devient la suivante](code.svg)

```basic keys=RENDEZ,Space,VOUS,Space,A,Space,L,Space,IGLOO,Enter
10 INPUT "TON MESSAGE ? "; M$
20 LET S$ = ""
30 FOR I = 1 TO LEN(M$)
40 LET C = ASC(MID$(M$, I, 1))
50 IF C >= 65 AND C <= 90 THEN LET C = C + 1
60 IF C = 91 THEN LET C = 65
70 LET S$ = S$ + CHR$(C)
80 NEXT I
90 PRINT "EN CODE : "; S$
```

La ligne 50 ne déplace que les majuscules : les espaces restent des
espaces. La ligne 60 renvoie à A la lettre qui suit Z.

> [think] Comment lirais-tu un message en code ? Change la ligne 50 pour
> enlever 1, et la ligne 60 pour transformer 64 en 90.

## Continue d'essayer

- Déplace chaque lettre de trois places au lieu d'une.
- Écris le programme qui décode le message, et essaie-le avec un ami.

::: adult
Ces numéros sont les codes ASCII, les mêmes sur presque tous les
ordinateurs. Les lettres accentuées n'en font pas partie, ce qui explique
aussi pourquoi ce BASIC écrit sans accents. Un code qui déplace chaque
lettre d'un nombre fixe de places s'appelle un chiffre de César, d'après
Jules César, qui en aurait utilisé un.
:::
