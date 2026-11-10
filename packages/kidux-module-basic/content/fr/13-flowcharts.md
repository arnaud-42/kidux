---
source_sha256 = "0dc3a785278d0a832edbaa6b674dc93690b141abd5f360347c7e91618b586011"
---
# Les organigrammes : le dessiner d'abord

Avant d'écrire un programme, ça aide de le dessiner. Un **organigramme**
est le dessin d'un programme : des cases pour ce qu'il faut faire, et des
flèches pour l'ordre.

![Les formes d'un organigramme](flowchart.svg)

- Une case aux coins arrondis, c'est le début ou la fin.
- Une case penchée, c'est quelque chose qu'on demande ou qu'on montre.
- Une case simple, c'est quelque chose qu'on calcule, comme une somme.
- Un losange, c'est une question avec deux sorties, oui et non : un `IF`.

> [point] Dessine-le d'abord sur du papier, au crayon. Les flèches qui
> remontent sont des boucles.

## Du dessin au programme

Un organigramme pour *demander un nombre de 1 à 10, et redemander tant
qu'il n'est pas bon* : début, demander, le losange *est-il de 1 à 10 ?*,
non remonte, oui continue, le montrer, fin. Le voici en BASIC :

```basic keys=12,Enter,7,Enter
10 INPUT "UN NOMBRE DE 1 A 10 ? "; N
20 IF N < 1 OR N > 10 THEN 10
30 PRINT "MERCI. DEUX FOIS "; N; " FONT "; N * 2
```

`OR` veut dire *l'un ou l'autre* : si le nombre est trop petit ou trop
grand, on redemande.

## Continue d'essayer

- Dessine l'organigramme du jeu de devinette du chapitre suivant avant de
  lire son programme.
- Dessine l'organigramme de ta matinée, du réveil jusqu'au départ de la
  maison.

::: adult
Les organigrammes rendent visible la forme d'un programme avant ses
détails. Ils sont particulièrement utiles quand un enfant est bloqué :
dessiner ce que le programme devrait faire montre en général l'endroit où
il part ailleurs.
:::
