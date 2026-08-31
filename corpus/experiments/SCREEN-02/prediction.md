# SCREEN-02 — quels modes déplacent vraiment l'écran (AVANT mesure)

GUARD-01 vient de reproduire SCREEN-01 : `SET_MODE 5` met le mode **rapporté**
à 5 et laisse le panneau sur HOME. Le registre note pourtant le mode 26 (Open)
comme **atteignable** par index brut. Les deux ne peuvent pas être vrais de la
même façon : ou le panneau suit certains modes et pas d'autres, ou il ne suit
jamais et l'observation de 26 était autre chose.

Manipulation : depuis HOME, un seul `SET_MODE` par mesure, l'opérateur lit
l'écran **après** — l'état persiste, aucune synchronisation n'est nécessaire.

| # | Envoi | Prédiction | p |
|---|---|---|---|
| 1 | `mode setup` (16) | mode rapporté 16 ; écran : **le menu principal s'affiche**. 16 est un écran de navigation, pas une page de show | 0.5 |
| 2 | `mode 26 --experimental` (PROJECTS) | mode rapporté 26 ; écran : **la page Open s'affiche** — c'est ce que le registre dit atteignable | 0.7 |
| 3 | retour `mode home` (0) | mode rapporté 0 ; écran : HOME | 0.8 |

Lecture rivale à tuer : « le panneau ne suit jamais un `SET_MODE`, et ce qu'on
a pris pour le mode 26 atteint venait d'un geste sur le panneau ». Si 1 et 2
laissent l'écran sur HOME, c'est elle qui gagne, et le mode rapporté est une
variable d'état interne sans lien avec l'affichage.
