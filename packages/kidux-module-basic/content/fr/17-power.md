---
source_sha256 = "bbc1cd3ac40b73cc2de10442d8863ebdbd46fc36f46e4d5bcbdd117307f261f8"
---
# La cinquième opération

Tu connais quatre opérations : `+`, `-`, `*` et `/`. La cinquième est la
**puissance**, qui s'écrit `^`. `2 ^ 3` veut dire 2 multiplié par
lui-même trois fois : 2 × 2 × 2, ce qui fait 8.

```basic
10 PRINT 2 ^ 3
20 PRINT 10 ^ 2
30 PRINT 3 ^ 4
40 PRINT 5 ^ 1, 5 ^ 0
```

N'importe quel nombre à la puissance 0 vaut 1, et à la puissance 1, il
vaut lui-même.

## Les poissons du pingouin

Le pingouin passe un marché avec le pêcheur : un poisson le premier jour,
deux le deuxième, quatre le troisième, et chaque jour deux fois plus que
la veille, pendant autant de jours qu'un échiquier a de cases,
soixante-quatre. Le pêcheur trouve que ce n'est pas cher.

![Un poisson, deux, quatre, huit](board.svg)

```basic
10 LET F = 1
20 FOR D = 1 TO 30
30 PRINT "JOUR "; D; " : "; F; " POISSONS"
40 LET F = F * 2
50 NEXT D
```

Le jour 30, ça fait plus de cinq cents millions de poissons, et il reste
encore 34 jours. Le jour D, le pingouin reçoit `2 ^ (D - 1)` poissons :

```basic
10 PRINT "JOUR 64 : "; 2 ^ 63; " POISSONS"
20 PRINT "EN TOUT : "; 2 ^ 64 - 1
```

> [cheer] Doubler fait grandir plus vite que tout ce que tu peux compter.
> Pauvre pêcheur !

## Les très grands nombres

Quand un nombre a trop de chiffres, l'ordinateur l'écrit en abrégé :

```basic
10 PRINT 10 ^ 20
20 PRINT 10 ^ 21
30 PRINT 2 ^ 100
```

`1e+21` veut dire 1 suivi de 21 zéros. Le nombre après `e+` dit de
combien de places la virgule se déplace vers la droite. Les très grands
nombres ne sont plus exacts : un nombre calculé dans un `PRINT` garde
environ seize chiffres, et un nombre gardé dans une boîte environ sept.

## Des boîtes avec plus de chiffres

Une boîte garde environ sept chiffres. Mets-y un nombre plus long, et les
derniers chiffres sont perdus :

```basic
10 LET A = 123456789
20 PRINT A
```

Il écrit 123456792 : c'est proche, mais ce n'est pas le nombre que tu as
mis. Une boîte dont le nom finit par `#` est une boîte plus grande, qui
garde environ seize chiffres, comme un `PRINT` :

```basic
10 LET A = 123456789
20 LET B# = 123456789
30 PRINT A, B#
```

> [point] De même que `$` à la fin d'un nom veut dire une boîte pour les
> mots, `#` veut dire une boîte avec de la place pour plus de chiffres.
> Utilise-en une quand un nombre est long et que chaque chiffre compte,
> comme pour l'horloge de l'ordinateur au chapitre 30.

## Continue d'essayer

- Combien de jours faut-il pour que le pingouin reçoive plus de mille
  poissons en un jour ? Et plus d'un million ?
- Écris les puissances de 3, de `3 ^ 0` à `3 ^ 10`.
- Mets 16777217 dans une boîte ordinaire et dans une boîte `#`, et écris
  les deux.

::: adult
L'histoire est la vieille légende des grains de riz sur un échiquier,
racontée avec des poissons. Les derniers nombres ne sont pas exacts : un
calcul garde environ seize chiffres significatifs, et une variable, en
simple précision comme dans les BASIC de l'époque, environ sept. `#`
marque une variable en double précision, avec seize chiffres ; le guide
n'en utilise une que là où c'est nécessaire, pour l'horloge.
:::
