---
source_sha256 = "0a17822b5a1d2ea129c1e3498e66c358a3b72ae33131ec8587ae107452a1221e"
---
# Dans l'ordinateur

Chaque ordinateur a trois parties qui comptent pour un programme. Le
**clavier**, c'est par là que les choses entrent. La **mémoire**, c'est là
que l'ordinateur garde ce sur quoi il travaille : les boîtes du chapitre 3
y habitent. L'**écran**, c'est par là que les choses sortent.

![Le clavier, la mémoire et l'écran](inside.svg)

Quand tu appuies sur **Lancer**, ton programme va dans la mémoire, et
l'ordinateur fait ses lignes une par une. Chaque boîte commence vide : une
boîte à nombre contient 0 et une boîte à mots ne contient rien du tout.
Lance celui-ci deux fois :

```basic
10 PRINT "POISSONS AVANT : "; POISSONS
20 LET POISSONS = POISSONS + 5
30 PRINT "POISSONS APRES : "; POISSONS
```

Il dit 0 puis 5, à chaque fois. Quand le programme se termine, ses boîtes
sont vidées, et le lancement suivant repart de rien.

> [think] Alors, que garde l'ordinateur ? Ton programme reste dans
> l'éditeur, même quand tu fermes BASIC. Un programme que tu enregistres
> est gardé dans un fichier aussi longtemps que tu veux. Mais les boîtes
> n'existent que pendant que le programme tourne.

## Les bits

Dans la mémoire, tout est fait de minuscules interrupteurs qu'on appelle
des **bits**. Un bit est soit éteint, soit allumé : 0 ou 1. Huit bits
ensemble forment un **octet**, et un octet peut contenir n'importe quel
nombre entier de 0 à 255. Chaque bit vaut deux fois le précédent :

```basic
10 LET V = 1
20 FOR B = 1 TO 8
30 PRINT "LE BIT "; B; " VAUT "; V
40 LET V = V * 2
50 NEXT B
```

Additionne-les tous, 1 + 2 + 4 + … + 128, et tu obtiens 255, le plus
grand nombre qu'un octet peut contenir. Une lettre tient aussi dans un
octet : le chapitre 28 montre quel nombre est chaque lettre.

## Continue d'essayer

- Change la ligne 20 du premier programme pour ajouter 10 au lieu de 5.
  Que dit-il la deuxième fois que tu le lances ?
- Fais aller le programme des bits jusqu'à 16 bits.

::: adult
L'idée de ce chapitre est qu'une variable ne vit que pendant que le
programme tourne, et que le programme lui-même est autre chose, gardé dans
l'éditeur et dans des fichiers. La mémoire d'un ordinateur se mesure en
octets : des millions, qu'on appelle des mégaoctets, et des milliards, des
gigaoctets.
:::
