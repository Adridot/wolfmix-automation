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

## Suite, prédite après 1 et 2 mais AVANT 4 et 5

Mesuré : 5 et 16 ne déplacent pas l'écran, **26 le déplace**. Lecture posée :
`SET_MODE` ouvre un écran **modal** ; il ne sait pas re-sélectionner une page
ordinaire, dont l'affichage appartient à l'état des touches du panneau.

| # | Envoi, depuis la page Open (26) | Prédiction | p |
|---|---|---|---|
| 4 | `mode presets` (5) | mode rapporté 5, mais l'écran **reste sur Open** — le registre dit que 26 ne se quitte pas par 0/5/16 | 0.75 |
| 5 | `mode 1 --experimental` (COLOR) | l'écran **quitte** le modal ; le registre donne l'index 1 comme échappatoire | 0.7 |

Si 5 quitte le modal alors que 5 (la mesure 4) ne fait rien, « seuls les modaux
sont poussables » est trop simple : il faudra dire pourquoi l'index 1 agit.

## Mesure 6, prédite avant d'être faite

4 et 5 ont réfuté « seuls les modaux sont poussables » : depuis le modal Open,
l'index 5 n'a rien fait et l'index 1 a ouvert COLOR FX — une page ordinaire.
Reste deux lectures rivales :

- **la cible décide** — certains index sont poussables (1, 26), d'autres non
  (5, 16) ;
- **l'écran de départ décide** — depuis HOME rien ne passe, depuis une autre
  page tout passe.

| # | Envoi, depuis COLOR FX | Si « la cible décide » | Si « le départ décide » | p |
|---|---|---|---|---|
| 6 | `mode presets` (5) | l'écran reste sur COLOR FX | l'écran passe sur PRESET | 0.5 / 0.5 |

## Mesures 7 et 8, prédites avant d'être faites

Mesure 6 : depuis COLOR FX, l'index 5 ne bouge rien. **C'est la cible qui
décide.** Poussables jusqu'ici : 1 (COLOR FX), 26 (Open). Inertes : 5 (PRESET),
16 (SETUP). Le seul motif visible est que 1 est une page **FX**.

| # | Envoi | Prédiction | p |
|---|---|---|---|
| 7 | `mode move` (3) | l'écran passe sur MOVE FX — les trois pages FX sont poussables | 0.7 |
| 8 | `mode beam` (4) | l'écran passe sur BEAM FX, même raison | 0.7 |

Si 7 et 8 passent, la règle mesurée devient « les trois pages FX et le modal
Open se poussent depuis l'hôte ; PRESET et SETUP non », et elle est **utile** :
c'est ce qu'on peut piloter sans toucher au panneau. Si l'une des deux échoue,
« page FX » n'est pas le critère et on redescend à une liste d'index.
