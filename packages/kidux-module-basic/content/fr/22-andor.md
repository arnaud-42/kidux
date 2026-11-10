---
source_sha256 = "6c4a3c91ef0979c35c3fe157c6db47c5a2b694849866ddfbbb294dc4d2ba5390"
---
# AND et OR

Parfois, une seule question ne suffit pas. Fait-il froid **et** est-ce
qu'il neige ? Alors c'est un jour pour faire un bonhomme de neige.
Pleut-il **ou** est-ce qu'il neige ? Alors il te faut un manteau.

- `AND` dit oui seulement quand les **deux** côtés disent oui.
- `OR` dit oui quand **l'un ou l'autre** côté, ou les deux, disent oui.

```basic keys=OUI,Enter,NON,Enter
10 INPUT "FAIT-IL FROID ? "; C$
20 INPUT "EST-CE QU'IL NEIGE ? "; S$
30 IF C$ = "OUI" AND S$ = "OUI" THEN PRINT "FAISONS UN BONHOMME DE NEIGE !"
40 IF C$ = "OUI" OR S$ = "OUI" THEN PRINT "METS TON MANTEAU."
50 IF C$ = "NON" AND S$ = "NON" THEN PRINT "UN JOUR POUR LE PARC."
```

## Attraper une mauvaise réponse

Quand un programme demande un nombre de 1 à 9, un programme soigneux dit
non à tout le reste et redemande :

```basic keys=0,Enter,15,Enter,4,Enter
10 INPUT "UN NOMBRE DE 1 A 9 ? "; N
20 IF N < 1 OR N > 9 THEN PRINT "DE 1 A 9, S'IL TE PLAIT": GOTO 10
30 PRINT "MERCI. VA POUR "; N; "."
```

## Le mot de passe de l'igloo

```basic keys=POISSON,Enter,GLACE,Enter,BOULEDENEIGE,Enter
10 LET T = 0
20 INPUT "MOT DE PASSE ? "; P$
30 LET T = T + 1
40 IF P$ <> "BOULEDENEIGE" AND T < 3 THEN PRINT "NON. ESSAIE ENCORE.": GOTO 20
50 IF P$ = "BOULEDENEIGE" THEN PRINT "BIENVENUE DANS L'IGLOO !" ELSE PRINT "LA PORTE RESTE FERMEE."
```

Tu as trois essais. La ligne 40 ne redemande que tant que le mot de passe
est faux **et** qu'il reste des essais.

> [think] `NOT` change oui en non et non en oui : `IF NOT (N = 5)` revient
> au même que `IF N <> 5`.

## Continue d'essayer

- Donne à l'igloo deux mots de passe qui l'ouvrent tous les deux.
- Demande un jour de la semaine et une heure, et dis si la boutique est
  ouverte.

::: adult
Les conditions reliées par `AND` et `OR` sont l'endroit où la logique
entre dans la programmation. Dire la condition à voix haute, *faux et
encore des essais*, est le moyen le plus sûr de ne pas se tromper. Dans ce
BASIC, une condition vraie vaut -1 et une condition fausse 0, ce que le
guide n'a jamais besoin de montrer.
:::
