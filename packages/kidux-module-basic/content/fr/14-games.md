---
source_sha256 = "00ed99536ac4a14140af9d7f1a9a9fd7f424efcf92e5e4886a324e50b4fdde75"
---
# Des jeux à faire

Tu en sais maintenant assez pour faire des jeux. Chacun d'eux n'utilise
que ce que les chapitres précédents ont appris. Tape-les, joue, et
ensuite change-les.

## L'entraîneur de tables

```basic keys=8,Enter,24,Enter,32,Enter,40,Enter
10 INPUT "QUELLE TABLE ? "; T
20 FOR N = 3 TO 5
30 PRINT T; " FOIS "; N; " ? ";
40 INPUT "", A
50 IF A = T * N THEN PRINT "JUSTE !" ELSE PRINT "NON, CA FAIT "; T * N
60 NEXT N
```

## Cache-cache

Le pingouin se cache derrière l'un des dix rochers. Trouve-le !

![Dix rochers dans la neige](garden.svg)

```basic keys=3,Enter,5,Enter,1,Enter,2,Enter,4,Enter,6,Enter,7,Enter,8,Enter,9,Enter,10,Enter
10 RANDOMIZE
20 LET R = INT(RND * 10) + 1
30 LET ESSAIS = 0
40 INPUT "QUEL ROCHER, DE 1 A 10 ? "; N
50 LET ESSAIS = ESSAIS + 1
60 IF N = R THEN 90
70 PRINT "PAS LA..."
80 GOTO 40
90 PRINT "TROUVE ! EN "; ESSAIS; " ESSAIS"
```

## Devine mon nombre

```basic keys=50,Enter,25,Enter,75,Enter,12,Enter,37,Enter,62,Enter,87,Enter,6,Enter,18,Enter,31,Enter,43,Enter,56,Enter,68,Enter,81,Enter,93,Enter,1,Enter,2,Enter,3,Enter,4,Enter,5,Enter
10 RANDOMIZE
20 LET R = INT(RND * 100) + 1
30 LET ESSAIS = 0
40 INPUT "MON NOMBRE EST DE 1 A 100. DEVINE : "; G
50 LET ESSAIS = ESSAIS + 1
60 IF G < R THEN PRINT "PLUS GRAND !"
70 IF G > R THEN PRINT "PLUS PETIT !"
80 IF G <> R AND ESSAIS < 20 THEN 40
90 IF G = R THEN PRINT "OUI ! EN "; ESSAIS; " ESSAIS" ELSE PRINT "C'ETAIT "; R
```

> [think] Quel est le premier essai le plus malin ? Pense aux moitiés.

## Le liseur de pensées

L'ordinateur devine le nombre auquel tu penses.

```basic keys=Enter,Enter,Enter,Enter,23,Enter
10 PRINT "PENSE A UN NOMBRE. NE ME LE DIS PAS !"
20 INPUT "APPUIE SUR ENTREE QUAND TU ES PRET", K$
30 PRINT "MULTIPLIE-LE PAR 2"
40 INPUT "APPUIE SUR ENTREE", K$
50 PRINT "AJOUTE 10"
60 INPUT "APPUIE SUR ENTREE", K$
70 PRINT "DIVISE-LE PAR 2"
80 INPUT "APPUIE SUR ENTREE", K$
90 INPUT "DIS-MOI CE QUE TU AS MAINTENANT : "; X
100 PRINT "TU AS PENSE A "; X - 5
```

> [cheer] Comment ça marche ? Note ce qui arrive au nombre, étape par
> étape, et tu verras le truc.

## Continue d'essayer

- Ne donne que cinq essais au pingouin de cache-cache.
- Dans l'entraîneur, demande toute la table, de 1 à 10, et compte les
  bonnes réponses.
- Invente ton propre jeu : un quiz sur ton animal préféré.

::: adult
Ces jeux rassemblent les premiers chapitres. Le liseur de pensées est
bon à expliquer ensemble : doubler, ajouter 10 et diviser par deux
laisse le nombre plus 5, quel qu'il soit.
:::
