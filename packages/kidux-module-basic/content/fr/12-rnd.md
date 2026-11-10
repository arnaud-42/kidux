---
source_sha256 = "cfa62060fc952829f8850cddcc156e75f5f66b7f64f3eaa191e545718a3fc13c"
---
# RND : le hasard

`RND` donne un nombre que personne ne peut deviner : un nombre au hasard,
à partir de 0 et jusqu'à 1, sans jamais atteindre 1. Il est différent à
chaque fois.

```basic
10 RANDOMIZE
20 FOR N = 1 TO 5
30 PRINT RND
40 NEXT N
```

`RANDOMIZE`, au début, mélange les nombres, pour que chaque lancement
soit différent.

## Un dé

Un dé donne 1, 2, 3, 4, 5 ou 6. Multiplie `RND` par 6, garde la partie
entière avec `INT`, et ajoute 1 :

![Un dé](dice.svg)

```basic
10 RANDOMIZE
20 LET D = INT(RND * 6) + 1
30 PRINT "TU AS FAIT UN "; D
```

Chaque fois que tu appuies sur Lancer, tu lances le dé.

## Cent lancers

Combien de cinq sortent en cent lancers ? Personne ne le sait avant
d'essayer, et l'ordinateur peut essayer très vite.

```basic
10 RANDOMIZE
20 LET CINQ = 0
30 FOR T = 1 TO 100
40 LET D = INT(RND * 6) + 1
50 IF D = 5 THEN LET CINQ = CINQ + 1
60 NEXT T
70 PRINT "EN 100 LANCERS, "; CINQ; " FOIS LE CINQ"
```

> [cheer] Lance-le plusieurs fois. La réponse est souvent proche de 16 ou
> 17, un sixième de 100, mais presque jamais exactement la même.

## Continue d'essayer

- Lance mille fois au lieu de cent.
- Compte les six en plus des cinq.
- Lance deux dés et additionne-les.

::: adult
`INT(RND * N) + 1` donne un nombre entier de 1 à N, chacun aussi probable
que les autres. Simuler beaucoup de lancers est une première approche,
ludique, des probabilités ; il vaut la peine de demander à l'enfant de
deviner avant de lancer.
:::
