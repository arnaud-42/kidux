---
source_sha256 = "28f373b2b1fb157e98ff02d9864b50331fcbeb44726b982dba340fd72d3fbcbc"
---
# LET : des boîtes avec un nom

Un ordinateur retient des choses dans des boîtes de sa mémoire, et chaque
boîte a un nom. Une boîte comme ça s'appelle une **variable**. `LET` met
quelque chose dans une boîte.

![Des boîtes avec un nom](boxes.svg)

```basic
10 LET POISSONS = 12
20 PRINT POISSONS
```

La boîte s'appelle `POISSONS`, et elle contient le nombre 12.
`PRINT POISSONS`, sans guillemets, écrit ce qu'il y a dans la boîte, pas
son nom.

> [think] Avec des guillemets, `PRINT "POISSONS"` écrit le mot POISSONS.
> Sans eux, `PRINT POISSONS` écrit 12. Essaie les deux !

## Les calculs

L'ordinateur est très fort en calcul. Il utilise `+` et `-`, `*` pour
« fois » et `/` pour « divisé par ».

```basic
10 LET POISSONS = 12
20 LET AMIS = 4
30 LET CHACUN = POISSONS / AMIS
40 PRINT "CHAQUE AMI RECOIT "; CHACUN; " POISSONS"
50 LET POISSONS = POISSONS + 10
60 PRINT "MAINTENANT IL Y EN A "; POISSONS
```

La ligne 50 a l'air bizarre : elle veut dire *prends ce qu'il y a dans
POISSONS, ajoute 10, et remets le résultat dans POISSONS*. Une boîte peut
changer de contenu aussi souvent que tu veux : c'est pour ça qu'on
l'appelle une variable.

## Des boîtes pour les mots

Une boîte dont le nom finit par `$` contient des mots au lieu de nombres.
Les mots se mettent entre guillemets, et `+` les colle ensemble.

```basic
10 LET A$ = "BONHOMME"
20 LET B$ = " DE NEIGE"
30 PRINT A$ + B$
```

Tu peux même oublier le mot `LET` : `POISSONS = 12` veut dire la même
chose.

## Continue d'essayer

- Calcule combien de pattes ont quatre pingouins, avec une variable pour
  chaque chose.
- Fais une phrase en collant trois boîtes de mots.
- Que se passe-t-il si tu fais `PRINT` d'une boîte que tu n'as jamais
  remplie ?

::: adult
Les variables avec `$` sont des variables de chaînes de caractères. Les
nombres et les chaînes ne se mélangent pas : `A = "NEIGE"` ne donne pas
d'erreur avec ce BASIC, mais laisse A à 0 ; il vaut donc la peine de
montrer à l'enfant de quelle sorte est chaque boîte. Une boîte jamais
remplie contient 0, ou une chaîne vide.
:::
