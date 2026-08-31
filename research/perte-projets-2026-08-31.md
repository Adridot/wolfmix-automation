# Quatre projets perdus sur le contrôleur — daté, et récupérable

Constat de l'opérateur le 2026-08-31 : le projet `f2737ec3` n'est plus sur le
W1, sans qu'il l'ait supprimé. Voici ce que les traces disent, parce qu'une
perte de données non expliquée vaut d'être documentée aussi soigneusement qu'un
champ décodé.

## La chronologie, depuis les journaux du harnais

| Date | `projectCount` | Source |
|---|---|---|
| 2026-08-25, init | **4** | `snapshots/initial-*/manifest.json` |
| 2026-08-27 | 6 | journal du run `gen-03` |
| **2026-08-30**, run `SORT-01` | **6** | journal du run |
| **2026-08-31**, avant le déploiement MAP-06 | **2** | `beforeSettings` du run MAP-06 |
| 2026-08-31, après le déploiement | **2** | `afterSettings` du même run |

La perte est survenue **entre le 30 et le 31 août, hors de toute exécution du
harnais** : aucun run n'a tourné entre les deux. Le déploiement MAP-06 a trouvé
2 projets et en a laissé 2.

## Ce que le code peut et ne peut pas faire

`DELETE_PROJECT` n'est appelé qu'à un seul endroit — `restore_previous()`, sur
le **chemin de rollback d'un échec** — et il est doublement borné : l'UUID est
celui de l'expérience, dérivé du label, et le nom doit commencer par
`WMX EXP `. Le chemin nominal de `deploy` ne supprime rien.

Il fait en revanche une chose non anodine : **il redémarre le contrôleur**.

## Ce qui reste non expliqué

Quatre projets d'un coup, sans commande de suppression et sans run. Deux faits
du dépôt vont dans le même sens sans rien prouver :

- `getProfileList` est déjà revenu **tronqué** une fois, défaut transitoire
  réparé au redémarrage (`wolfmix-device-profile-fault`).
- Cette session a produit plusieurs fautes de lien : `Expected event 4,
  received event 21`, `Unsupported protobuf wire type 4`, un timeout — toutes
  réparées par une simple relance.

**[observed]** — l'appareil n'est pas parfaitement sain. Aucune lecture ne
survit à ce qu'on sait, et je n'en propose pas.

## La récupération

Le harnais snapshote **tous** les projets du contrôleur à l'init, pas seulement
celui de l'expérience. Les quatre du 25 août sont intacts :

```
.wolfmix-state/<uuid>/snapshots/initial-20260825T103338.112295Z/
    f2737ec3-…-10ec4c0d46d0.wpj   (projet opérateur) 44729 o
    d958f470-…-1b5bf4d1f2c9.wpj   WMX TEST ACC-04   38796 o
    06b84aa0-…-1b5bf4d1f2c9.wpj   WMX TEST ACC-05   38794 o
    1385cf30-…-1b5bf4d1f2c9.wpj   WMX TEST ACC-06   38791 o
```

Les quatre portent un en-tête SHA-1 valide et le SHA-256 annoncé par le
manifeste.

**Le piège.** `corpus/projects/f2737ec3-….wpj` porte le même UUID mais fait
**43329 octets** : c'est la copie **anonymisée**, pas celle de l'appareil. Elle
ne doit pas servir à restaurer. La copie authentique est celle du snapshot,
44729 octets, `adaf177d906176b4…`.

## Ce que la restauration demande

`wolfmix.encode_project()` refuse tout nom qui ne commence pas par `WMX EXP `,
et c'est délibéré : le garde-fou existe pour ne **jamais écraser** un projet de
l'opérateur. Restaurer un projet **absent** de l'appareil n'écrase rien, mais
demande de construire la trame `SET_PROJECT` à la main.

Un script à usage unique le fait, et refuse d'écrire si l'UUID est présent —
il ne redémarre pas le contrôleur et relit le projet pour confirmer. Il n'est
pas versionné : ce n'est pas un outil, c'est un pansement, et le laisser dans
le dépôt inviterait à l'utiliser.

## La leçon d'outillage

L'instantané d'init est ce qui a sauvé la mise, et il a été pris une fois, le
25 août. Rien ne le rafraîchit. Un projet créé après cette date et perdu avant
le prochain `init` ne serait **récupérable nulle part**.
