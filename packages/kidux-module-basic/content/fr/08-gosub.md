---
source_sha256 = "280f2450044e5e15c0c5994d5d8300b77f221822f6263e0440015349e00fc34c"
---
# GOSUB et RETURN : un morceau qui sert plusieurs fois

Il arrive que les mêmes lignes servent à plusieurs endroits. Au lieu de
les écrire de nouveau, écris-les une fois, à la fin, et vas-y avec
`GOSUB`. `RETURN` revient juste après le `GOSUB` qui y était allé.

```basic
10 PRINT "PREMIERE QUESTION"
20 GOSUB 100
30 PRINT "DEUXIEME QUESTION"
40 GOSUB 100
50 PRINT "FIN"
60 END
100 PRINT "*-*-*-*-*-*-*-*"
110 RETURN
```

Les lignes 100 et 110 forment un **sous-programme** : un petit programme
à l'intérieur du grand.

> [oops] Regarde la ligne 60. Sans `END`, l'ordinateur continuerait tout
> seul dans le sous-programme, et son `RETURN` ne saurait pas où revenir.

## Un sous-programme qui en fait plus

```basic
10 FOR N = 1 TO 3
20 GOSUB 100
30 NEXT N
40 END
100 PRINT "LE PINGOUIN "; N; " FAIT COUCOU :"
110 PRINT "  BONJOUR !"
120 PRINT
130 RETURN
```

## Continue d'essayer

- Fais un sous-programme qui dessine un petit poisson avec des lettres,
  et utilise-le trois fois.
- Mets une longue ligne d'étoiles dans un sous-programme et utilise-la
  entre les questions de ton quiz.

::: adult
Un sous-programme est le premier pas vers l'organisation d'un programme
en parties, ce qui compte de plus en plus à mesure que les programmes
grandissent. Si le programme d'un enfant se termine par une erreur qui
parle d'un RETURN sans son GOSUB, il manque en général un `END` avant les
sous-programmes.
:::
