---
source_sha256 = "28ffb11d6fd422b1f3b0097b9cbb8fb66e71ba1854eb5901bf924de03f7c60b4"
---
# Bonjour, ordinateur

Un ordinateur fait exactement ce qu'on lui dit, une chose après l'autre,
très vite. Une liste d'ordres pour lui s'appelle un **programme**, et
**BASIC** est un langage pour écrire des programmes. C'est le langage que
parlaient les premiers ordinateurs familiaux, il y a quarante ans, et
c'est toujours une très bonne façon de commencer.

À gauche de cette fenêtre se trouve ton ordinateur. En haut, il y a
l'**éditeur**, où tu écris. En dessous, il y a les boutons. Et en dessous
d'eux, l'**écran**, où ton programme montre ce qu'il fait.

![L'éditeur, les boutons et l'écran](computer.svg)

> [point] Chaque ligne d'un programme BASIC commence par un numéro. Tape
> ces deux lignes dans l'éditeur, en appuyant sur Entrée à la fin de
> chacune.

```basic
10 PRINT "BONJOUR"
20 PRINT "JE SUIS UN ORDINATEUR"
```

Appuie maintenant sur **Lancer**. L'écran te dit bonjour. Ton premier
programme marche !

::: type-in
Chaque programme de ce guide a un bouton, *Tape-le pour moi*, qui le met
dans l'éditeur à ta place. Mais c'est mieux de le taper toi-même : c'est
comme ça que tes doigts apprennent où sont les touches.
:::

## Pourquoi 10, 20, 30 ?

L'ordinateur fait les lignes du haut de l'éditeur jusqu'en bas. Le
numéro au début d'une ligne est son nom : plus tard, tu verras des ordres
qui sautent à une ligne par son nom. Deux lignes ne peuvent pas avoir le
même nom.

On les numérote de 10 en 10 pour laisser de la place. Si tu veux une
nouvelle ligne entre la ligne 10 et la ligne 20, écris-la entre elles dans
l'éditeur et appelle-la 15.

> [think] Saurais-tu ajouter une ligne 15 qui dise quelque chose sur toi ?

## Continue d'essayer

- Change les mots entre les guillemets, et appuie de nouveau sur Lancer.
- Ajoute une ligne 30 avec une troisième phrase.
- Écris `PRIMT` au lieu de `PRINT`, exprès, et appuie sur Lancer.
  L'ordinateur te dit qu'il ne comprend pas, et à quelle ligne. Corrige-la
  et relance : tous les programmeurs corrigent des programmes toute la
  journée.

::: adult
Ce guide enseigne BASIC une idée par chapitre, et chaque idée s'essaie
tout de suite sur l'ordinateur. Laissez l'enfant taper les programmes ; le
bouton qui les tape est là pour les longs et pour les mains fatiguées. Un
enfant qui veut changer un programme pour voir ce qui se passe fait
exactement ce qu'il faut.

Le BASIC utilisé ici est wwwBASIC, un BASIC dans le style du QBasic des
PC, qui tourne dans le navigateur. Le guide est écrit pour lui. Ses lignes
s'exécutent dans l'ordre où elles sont écrites dans l'éditeur, et leurs
numéros sont leurs noms. Ses lettres sont celles des PC de l'époque, qui
n'avaient pas d'accents : c'est pourquoi les programmes du guide écrivent
sans accents.
:::
