---
source_sha256 = "3a0c33f29d68aedad13397e1944c57ca2ce61b0f0518adc1404cec217ebabe4d"
---
# IF, plus loin : les menus

Un programme qui fait plusieurs choses peut les proposer dans un
**menu** : une liste avec un numéro pour chacune, et une question.

`ON … GOTO` saute à la première ligne de sa liste quand la boîte contient
1, à la deuxième quand elle contient 2, et ainsi de suite. Quand le
nombre n'est pas dans la liste, il passe à la ligne suivante.

```basic keys=2,Enter
10 PRINT "LE CAFE DU PINGOUIN"
20 PRINT "1  SOUPE DE POISSON"
30 PRINT "2  GLACE"
40 PRINT "3  CHOCOLAT CHAUD"
50 INPUT "QUE DESIRES-TU ? "; C
60 ON C GOTO 100, 200, 300
70 PRINT "CE N'EST PAS AU MENU."
80 END
100 PRINT "UNE SOUPE DE POISSON, BIEN CHAUDE."
110 END
200 PRINT "UNE GLACE, BIEN FROIDE."
210 END
300 PRINT "UN CHOCOLAT CHAUD, AVEC UNE GUIMAUVE."
```

`END` arrête le programme à cet endroit, pour qu'une commande ne
continue pas dans la suivante.

## ELSE

`ELSE` dit quoi faire quand le `IF` n'est pas vrai. Tu l'as rencontré
dans les jeux du chapitre 14 :

```basic keys=7,Enter
10 INPUT "QUEL AGE AS-TU ? "; A
20 IF A < 8 THEN PRINT "LE PETIT TOBOGGAN" ELSE PRINT "LE GRAND TOBOGGAN"
```

## Un menu qui revient

```basic keys=1,Enter,2,Enter,3,Enter
10 PRINT
20 PRINT "1 DIRE BONJOUR   2 UNE BLAGUE   3 PARTIR"
30 INPUT "CHOISIS : "; C
40 ON C GOSUB 100, 200
50 IF C <> 3 THEN 10
60 PRINT "SALUT !"
70 END
100 PRINT "BONJOUR A TOI !"
110 RETURN
200 PRINT "QUEL EST LE COMBLE POUR UN PINGOUIN ? AVOIR FROID AUX PIEDS !"
210 RETURN
```

`ON … GOSUB` fait la même chose avec `GOSUB` : chaque choix est un
sous-programme qui revient au menu.

> [cheer] La plupart des programmes que tu utilises ont un menu. Les tiens
> aussi, maintenant.

## Continue d'essayer

- Ajoute une quatrième chose au café.
- Donne au menu qui revient un quatrième choix : une devinette.

::: adult
Un menu est la première structure de programme qu'un enfant peut
concevoir sur papier avant de taper : la liste des choix, et un morceau de
programme pour chacun.
:::
