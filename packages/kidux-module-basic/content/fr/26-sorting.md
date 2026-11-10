---
source_sha256 = "5fa7845960a57815adbab7a5e47442e9a3a63dbb43bc087074810e6d51555c22"
---
# Mettre les choses en ordre

L'ordinateur peut comparer des nombres avec `<` et `>`, et des mots
aussi : pour les mots, *plus petit* veut dire *plus tôt dans l'alphabet*.

```basic
10 IF 3 < 7 THEN PRINT "3 VIENT AVANT 7"
20 IF "ANA" < "TOM" THEN PRINT "ANA VIENT AVANT TOM"
30 IF "PIP" > "BEA" THEN PRINT "PIP VIENT APRES BEA"
```

## Échanger deux boîtes

Pour échanger ce que contiennent deux boîtes, il te faut une troisième
boîte, de secours : d'abord le poisson va dans la boîte de secours, puis
le flocon dans la boîte du poisson, puis le poisson de la boîte de secours
dans celle du flocon.

![Échanger avec une boîte de secours](swap.svg)

```basic
10 LET A = 3: LET B = 8
20 PRINT "AVANT : "; A; " ET "; B
30 LET S = A
40 LET A = B
50 LET B = S
60 PRINT "APRES : "; A; " ET "; B
```

> [oops] Sans la boîte de secours, `LET A = B` perdrait ce que contenait A,
> et les deux boîtes finiraient avec 8.

BASIC a aussi `SWAP A, B`, qui fait les trois étapes d'un coup.

## Trier des nombres

Le **tri à bulles** parcourt l'étagère en comparant chaque boîte avec la
suivante, et les échange quand elles sont dans le mauvais sens. Après un
passage, le plus grand nombre est remonté jusqu'au bout, comme une bulle ;
après assez de passages, tout est en ordre.

```basic
10 DIM N(6)
20 FOR I = 1 TO 6: READ N(I): NEXT I
30 FOR W = 1 TO 5
40 FOR I = 1 TO 6 - W
50 IF N(I) > N(I + 1) THEN SWAP N(I), N(I + 1)
60 NEXT I
70 NEXT W
80 FOR I = 1 TO 6: PRINT N(I); " ";: NEXT I
90 PRINT
100 DATA 42, 7, 19, 3, 25, 11
```

## Trier des prénoms

Le même programme trie des mots, avec des boîtes à mots :

```basic
10 DIM N$(6)
20 FOR I = 1 TO 6: READ N$(I): NEXT I
30 FOR W = 1 TO 5
40 FOR I = 1 TO 6 - W
50 IF N$(I) > N$(I + 1) THEN SWAP N$(I), N$(I + 1)
60 NEXT I
70 NEXT W
80 FOR I = 1 TO 6: PRINT N$(I): NEXT I
90 DATA TOM, ANA, PIP, LULU, BEA, MAX
```

## Continue d'essayer

- Trie les nombres du plus grand au plus petit. Quel signe changes-tu ?
- Écris l'étagère après chaque passage, pour regarder les nombres remonter
  comme des bulles.

::: adult
Les mots sont comparés lettre par lettre selon leurs codes (chapitre 28) :
les majuscules viennent donc avant les minuscules, et un mot avec un
accent peut ne pas arriver là où le met un dictionnaire. Le tri à bulles
est lent pour les longues listes, mais facile à suivre, et c'est pour ça
qu'on l'enseigne en premier.
:::
