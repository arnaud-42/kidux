---
source_sha256 = "568286770c0011c230c589b3bed437af7d7f92e84fac2bd2fb98bb0f3db1769e"
---
# PRINT : l'ordinateur écrit

`PRINT` écrit à l'écran tout ce qui se trouve entre les guillemets,
exactement tel quel.

```basic
10 PRINT "LE PINGOUIN VIT SUR LA GLACE"
20 PRINT "IL MANGE DU POISSON"
30 PRINT
40 PRINT "ET IL ADORE LA NEIGE"
```

Un `PRINT` sans rien derrière écrit une ligne vide, comme la ligne 30.

## Quand BASIC ne comprend pas

Ce programme a une erreur exprès, à la ligne 20 : `PIRNT` au lieu de
`PRINT`. Tape-le tel quel, et appuie sur **Lancer**.

```basic mistake
10 PRINT "LE PINGOUIN VIT SUR LA GLACE"
20 PIRNT "IL MANGE DU POISSON"
30 PRINT "ET IL ADORE LA NEIGE"
```

Rien ne s'écrit, pas même la ligne 10. BASIC lit tout le programme avant
d'en lancer la moindre partie, et il s'arrête à une ligne qu'il ne
comprend pas. Le texte sous l'écran dit quelle ligne, et l'éditeur la
signale. Écris `PRINT` correctement à la ligne 20 et appuie de nouveau sur
**Lancer**.

> [oops] Un guillemet oublié au début des mots fait la même chose. Quand
> BASIC ne comprend pas une ligne, regarde d'abord l'orthographe et les
> guillemets.

## Virgules et points-virgules

Après un `PRINT`, tu peux mettre plusieurs choses, séparées par `;` ou
par `,`. Un point-virgule écrit la chose suivante juste après ; une
virgule saute d'abord un peu plus loin sur la ligne.

```basic
10 PRINT "BONHOMME"; "DE NEIGE"
20 PRINT "BONHOMME", "DE NEIGE"
30 PRINT "UN "; "DEUX "; "TROIS"
```

C'est l'espace à l'intérieur de `"UN "` qui sépare les mots.

## Dessiner avec des lettres

L'écran est fait de rangées de lettres : les lettres peuvent donc dessiner
des images.

```basic
10 PRINT "  *****"
20 PRINT " *     *"
30 PRINT "*  O O  *"
40 PRINT "*   ^   *"
50 PRINT " * --- *"
60 PRINT "  *****"
```

> [cheer] Quand tu commences un nouveau programme, appuie d'abord sur
> **Nouveau**, pour que les anciennes lignes ne se mélangent pas avec les
> nouvelles.

## Continue d'essayer

- Dessine une maison, un poisson ou une fusée avec des lettres.
- Écris ton prénom en grandes lettres faites de `#`.
- Mets une `,` puis un `;` entre deux mots, et regarde la différence.

::: adult
La virgule passe à la zone d'impression suivante, une colonne de quatorze
caractères de large ; le point-virgule n'ajoute rien. Les nombres écrits
avec `;` ne reçoivent pas d'espaces autour d'eux avec ce BASIC : le guide
met donc un `" "` entre eux quand ils doivent rester séparés.
:::
