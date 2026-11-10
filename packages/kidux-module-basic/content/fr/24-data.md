---
source_sha256 = "715820360a073cd69cf4bc9202809b1f2806fdc3eb930436aba50dc9da027b8f"
---
# READ, DATA et RESTORE

Les lignes `DATA` sont une réserve de choses que le programme lit dans
l'ordre avec `READ`. Elles peuvent contenir des mots et des nombres
ensemble.

```basic
10 FOR N = 1 TO 4
20 READ F$, G$
30 PRINT F$; " JOUE "; G$
40 NEXT N
50 DATA PIP, AU FOOTBALL, TOM, AUX ECHECS
60 DATA LULU, DU PIANO, BEA, A CACHE-CACHE
```

## Chercher

Pour trouver à quoi joue quelqu'un, lis les amis un par un jusqu'à ce que
le nom soit celui que tu veux. Le dernier `DATA` est une marque qui dit
*il n'y en a plus*, comme au chapitre 9 :

```basic keys=LULU,Enter
10 INPUT "QUEL AMI ? "; W$
20 READ F$, G$
30 IF F$ = "FIN" THEN PRINT "JE NE CONNAIS PAS "; W$: END
40 IF F$ = W$ THEN PRINT W$; " JOUE "; G$: END
50 GOTO 20
60 DATA PIP, AU FOOTBALL, TOM, AUX ECHECS
70 DATA LULU, DU PIANO, BEA, A CACHE-CACHE
80 DATA FIN, FIN
```

## Relire

`READ` se souvient de l'endroit où il en est. `RESTORE` le renvoie au
premier `DATA`, pour tout relire :

```basic keys=TOM,Enter,OUI,Enter,BEA,Enter,NON,Enter
10 INPUT "QUEL AMI ? "; W$
20 RESTORE
30 READ F$, G$
40 IF F$ = "FIN" THEN PRINT "JE NE CONNAIS PAS "; W$: GOTO 70
50 IF F$ = W$ THEN PRINT W$; " JOUE "; G$: GOTO 70
60 GOTO 30
70 INPUT "UN AUTRE ? "; A$
80 IF A$ = "OUI" THEN 10
90 DATA PIP, AU FOOTBALL, TOM, AUX ECHECS
100 DATA LULU, DU PIANO, BEA, A CACHE-CACHE
110 DATA FIN, FIN
```

> [point] Sans la ligne 20, la deuxième recherche commencerait là où la
> première s'est arrêtée, et raterait les amis d'avant.

## Continue d'essayer

- Ajoute tes propres amis et ce à quoi ils jouent.
- Fais un quiz à partir de `DATA` : une question et sa réponse sur chaque
  ligne.

::: adult
`RESTORE` peut aussi nommer une ligne, `RESTORE 100`, pour lire à partir de
cette ligne `DATA`. Chercher dans une liste un élément à la fois est la
façon dont un ordinateur trouve les choses quand elles ne sont pas en
ordre ; le chapitre 26 les met en ordre.
:::
