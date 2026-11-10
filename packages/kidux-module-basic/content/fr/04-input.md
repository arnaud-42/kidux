---
source_sha256 = "04b1740b592c330eb4a885bb84b254f8dfcbff205aff88eeba159271be8be7fc"
---
# INPUT : parler avec l'ordinateur

Jusqu'ici, l'ordinateur parlait et toi, tu écoutais. `INPUT` inverse les
rôles : l'ordinateur s'arrête, pose une question et attend que tu tapes
une réponse et que tu appuies sur Entrée. La réponse va dans une boîte.

```basic keys=Leo,Enter
10 INPUT "COMMENT T'APPELLES-TU ? "; N$
20 PRINT "BONJOUR, "; N$
```

Appuie sur Lancer, tape ton prénom, appuie sur Entrée. L'ordinateur te
répond.

> [point] La question se met entre guillemets, puis un point-virgule, puis
> la boîte pour la réponse. Mets une espace avant le dernier guillemet,
> pour que ta réponse ne soit pas collée à la question.

## Des nombres comme réponses

Si le nom de la boîte n'a pas de `$`, la réponse est un nombre, et
l'ordinateur peut faire des calculs avec.

```basic keys=7,Enter
10 INPUT "QUEL AGE AS-TU ? "; AGE
20 PRINT "L'AN PROCHAIN, TU AURAS "; AGE + 1
30 PRINT "DANS DIX ANS, "; AGE + 10
```

## Un programme qui te connaît

```basic keys=Ana,Enter,9,Enter,PIZZA,Enter
10 INPUT "TON PRENOM ? "; N$
20 INPUT "TON AGE ? "; A
30 INPUT "TON PLAT PREFERE ? "; F$
40 PRINT
50 PRINT N$; " A "; A; " ANS ET ADORE "; F$
60 PRINT "DANS "; 100 - A; " ANS, "; N$; " AURA 100 ANS"
```

> [cheer] Maintenant, le même programme dit quelque chose de différent à
> chaque personne qui le lance. C'est ce qui rend les programmes utiles.

## Continue d'essayer

- Demande deux nombres et écris leur somme.
- Demande un animal et une couleur, et écris une phrase avec les deux.
- Tape un mot quand l'ordinateur demande un nombre. Que fait-il ?

::: adult
`INPUT` avec une boîte qui finit par `$` accepte n'importe quel texte ;
sans `$`, un nombre. Avec ce BASIC, un mot tapé à la place d'un nombre
donne `NaN`, « not a number », « pas un nombre », au lieu de reposer la
question. C'est un bon moment pour parler de la vérification de ce que
tapent les gens, ce que le chapitre 22 fait correctement.
:::
