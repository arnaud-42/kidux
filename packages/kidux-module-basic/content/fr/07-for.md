---
source_sha256 = "313f3612a5b56873dcca4c77acbbc9b177c1396fee089d55dc5ac7eee190928f"
---
# FOR et NEXT : la boucle qui compte

Compter avec `GOTO` demande une boîte, un calcul et un saut. `FOR` fait
les trois d'un coup : il compte d'un nombre à un autre, et fait les lignes
entre `FOR` et `NEXT` une fois pour chaque nombre.

```basic
10 FOR N = 1 TO 5
20 PRINT "PINGOUIN NUMERO "; N
30 NEXT N
40 PRINT "CINQ PINGOUINS !"
```

![Une boucle tourne en rond](loop.svg)

`NEXT N` veut dire *le N suivant, s'il te plaît*. Quand N a valu 5, la
boucle est finie et l'ordinateur passe à la ligne 40.

> [cheer] Chaque `FOR` a besoin de son `NEXT`. Si tu l'oublies,
> l'ordinateur te dit qu'il manque quelque chose à la fin.

## STEP

`STEP` dit de combien compter à chaque fois. Il peut même compter à
l'envers.

```basic
10 FOR N = 0 TO 20 STEP 5
20 PRINT N
30 NEXT N
40 FOR N = 10 TO 1 STEP -1
50 PRINT N; " ";
60 NEXT N
70 PRINT "DECOLLAGE !"
```

## Une table

```basic
10 FOR N = 1 TO 10
20 PRINT N; " FOIS 3 FONT "; N * 3
30 NEXT N
```

## Continue d'essayer

- Écris ton prénom dix fois.
- Écris la table de 7, ou demande avec `INPUT` quelle table écrire.
- Compte de 100 jusqu'à 0, de dix en dix.

::: adult
La boîte qui suit `FOR` est une variable ordinaire : à l'intérieur de la
boucle, on peut l'écrire et s'en servir dans des calculs. Une boucle dans
une autre boucle, c'est pour le chapitre 21 ; pour l'instant, une seule
suffit.
:::
