---
source_sha256 = "c2525c8e5dda011c7a7121086674a1619791e65d142fc7fd979237d7b60cc725"
---
# GOTO : saute !

`GOTO` envoie l'ordinateur à une autre ligne, par son numéro, et il
continue à partir de là. Un saut en arrière fait refaire les mêmes lignes
à l'ordinateur.

```basic forever
10 PRINT "LE PINGOUIN GLISSE SUR LA PENTE"
20 GOTO 10
```

Ce programme ne finit jamais : la ligne 20 renvoie toujours l'ordinateur à
la ligne 10. Appuie sur **Arrêter**, ou sur la touche Échap, pour le
terminer.

> [oops] Un programme qui tourne en rond sans fin s'appelle une boucle.
> Quand la tienne ne veut pas s'arrêter, Échap marche toujours.

## Compter

Une boucle avec une boîte qui grandit sait compter.

```basic forever
10 LET N = 0
20 LET N = N + 2
30 PRINT N
40 GOTO 20
```

L'ordinateur compte de deux en deux plus vite que tu ne peux lire.
Arrête-le, et remonte l'écran des yeux.

## Un saut en avant

`GOTO` peut aussi sauter en avant, par-dessus des lignes qu'il ne doit
pas faire. `END` termine le programme.

```basic
10 PRINT "UN"
20 GOTO 40
30 PRINT "CETTE LIGNE EST SAUTEE"
40 PRINT "DEUX"
50 END
```

> [think] Si tu fais `GOTO` vers une ligne qui n'est pas dans le
> programme, l'ordinateur te le dit avant de commencer. Essaie `GOTO 99`.

## Continue d'essayer

- Fais compter le programme de cinq en cinq, ou de dix en dix.
- Compte à rebours depuis 100 en enlevant au lieu d'ajouter.
- Fais une table d'addition : un nombre qui grandit de un à chaque fois,
  et ce nombre plus 3, écrits côte à côte.

::: adult
`GOTO` est la façon dont les premiers ordinateurs familiaux faisaient des
boucles, et voir une boucle qui ne finit jamais fait partie de
l'apprentissage. Les chapitres suivants donnent une fin aux boucles : `IF`
décide quand s'arrêter, et `FOR` compte tout seul. Échap, ou le bouton
Arrêter, termine n'importe quel programme, et rien n'est perdu : le
programme reste dans l'éditeur.
:::
