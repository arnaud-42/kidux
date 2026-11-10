---
source_sha256 = "228809a494d1115fafd88d913dc9ff43a55874e83b330154aa3c52ecc9d2869e"
---
# READ et DATA : une réserve de choses

Quand un programme a besoin de beaucoup de valeurs, `DATA` les garde dans
une liste, et `READ` les sort une par une, dans l'ordre.

```basic
10 READ A, B, C
20 PRINT A + B + C
30 DATA 5, 7, 4
```

`READ A, B, C` met la première valeur dans A, la suivante dans B, la
suivante dans C.

## Des mots dans DATA

`DATA` peut aussi contenir des mots, qu'on lit dans des boîtes avec `$`.

```basic
10 FOR N = 1 TO 3
20 READ NOM$, PLAT$
30 PRINT NOM$; " AIME "; PLAT$
40 NEXT N
50 DATA PIP, LE POISSON, TOM, LE GATEAU, LULU, LES POMMES
```

> [think] Que se passe-t-il si `READ` veut plus de valeurs que `DATA` n'en
> a ? Essaie de changer `3` en `4` à la ligne 10.

L'ordinateur dit qu'il n'y a plus de `DATA` à lire.

## Une marque qui dit stop

Pour lire une liste sans la compter, mets à la fin une valeur de plus qui
veut dire *c'est fini*, et laisse `IF` la guetter.

```basic
10 LET TOTAL = 0
20 READ N
30 IF N = -1 THEN 60
40 LET TOTAL = TOTAL + N
50 GOTO 20
60 PRINT "LE TOTAL EST "; TOTAL
70 DATA 3, 8, 12, 5, -1
```

## Continue d'essayer

- Garde les prénoms et les âges de cinq amis dans `DATA` et écris-les.
- Ajoute un sixième ami, sans rien changer d'autre que le `DATA`, dans le
  programme avec la marque.

::: adult
Les lignes `DATA` peuvent être n'importe où dans le programme ; à la fin,
c'est le plus clair. `RESTORE` recommence la lecture à la première
valeur, ce dont se sert le chapitre 24.
:::
