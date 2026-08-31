# UPLOAD-02 — la géométrie de la flash de ressources (AVANT mesure)

Deux journaux de WTOOLS conservés sur cette machine portent un *Upload Flash*
du 2026-08-30. Ils donnent un **compte** et un **rythme** de messages, jamais
un octet : la ligne écrite est `Sending: WmMsgType.setFlashDataChunks`, sans
longueur et sans charge utile. Ce qui suit déduit la géométrie de ce compte et
de la taille du fichier, et rien d'autre. C'est une inférence arithmétique,
elle est publiée `hypothesized`, et elle est écrite **avant** la mesure qui
peut la tuer.

## Ce qui est lu, et qui ne se prédit pas

| Lu dans les deux sessions | Valeur |
|---|---|
| Messages `setFlashDataChunks` par session | 180 |
| Le premier, refusé (`UNSAVED_PROJECT`) | 1 |
| Ceux qui suivent la sauvegarde du projet | 179 |
| Écart médian entre ces 179 | 163 ms (min 143, max 176) |
| Durée du train | 29,0 s et 28,3 s |
| `wolfmixFlash.bin` installé | 2 931 442 octets |

Les deux sessions ont la même forme, à un jour de mesure identique. C'est une
répétition, pas deux points indépendants.

## L'arithmétique

Si les 179 messages qui suivent portent le fichier entier et rien d'autre,
alors la taille de chunk est contrainte :

| Taille de chunk | Messages nécessaires | Dernier chunk |
|---|---|---|
| 2 048 | 1 432 | 754 |
| 4 096 | 716 | 2 802 |
| 8 192 | 358 | 6 898 |
| **16 384** | **179** | **15 090** |
| 32 768 | 90 | 15 090 |
| 65 536 | 45 | 47 858 |

Une seule tombe juste : **16 KiB**. 178 × 16 384 = 2 916 352, plus 15 090,
égale 2 931 442 — la longueur du fichier, exactement.

## La prédiction

La trame du lien est `9 + n` : `HEADER_SIZE = 9` dans
`tools/wolfmix_protocol.py` (version u8, taille u32, id de message u16,
event u16), puis la charge utile.

1. **1 message de contrôle**, puis **179 chunks**.
2. Chunks 1 à 178 : 16 384 octets de charge utile, soit **16 393 octets sur le
   lien**.
3. Chunk 179 : **15 090** octets, soit 15 099 sur le lien.
4. Somme des charges utiles = 2 931 442, au bit près.
5. Le message de contrôle ne porte pas de données de flash : c'est lui que
   l'appareil refuse quand le projet n'est pas sauvegardé, et c'est ce refus
   qui rend le compte lisible comme 1 + 179 plutôt que comme 180 chunks.

Le point 5 est le maillon faible et il est nommé comme tel : le journal ne
distingue pas les deux rôles, ils portent le même nom de message.

## Ce qui la réfuterait

| Observation | Ce qu'elle tue |
|---|---|
| Une écriture d'une taille autre que 16 393 dans le train | la taille de chunk, donc toute la table ci-dessus |
| 180 écritures porteuses de données, sans message court en tête | le découpage 1 + 179 : il ne reste alors plus de place pour un en-tête |
| Une longueur qui n'est pas `9 + n` sur le lien | la trame, et avec elle la lecture du protocole publiée ailleurs |
| Un compte de messages identique pour un fichier de taille différente | la géométrie n'est pas gouvernée par la longueur, et l'arithmétique ne prouve rien |
| Le firmware et la flash poussés dans le même train de messages | ce serait la réponse à la question frontière, dans le sens qui **arrête** le travail (`LEGAL.md`) |

Une mesure qui confirme le compte sans montrer une longueur ne confirme rien
de plus que ce qui est déjà lu.

## La mesure qui tranchera

**Pas une capture USB.** UPLOAD-01 a lu que le transport est un tty
(`/dev/cu.usbmodem…`, ouvert par `SerialPortAgent`) ; RELOAD-01 avait cherché
une capture USB sur cette machine et ne l'avait pas obtenue. L'instrument est
du côté hôte :

- soit `fs_usage` ou `dtrace` sur les écritures du processus WTOOLS vers le
  descripteur du tty — cela rend les **longueurs**, ce qui est exactement la
  variable en jeu ;
- soit un port série virtuel entre WTOOLS et l'appareil, qui rend les octets.

Les deux sont passifs sur le lien et n'envoient rien. Aucun des deux n'est dans
ce changement.

## Ce que je ne prédis pas

- Ce que l'appareil fait d'un premier message refusé — UPLOAD-04 écrit l'écart
  et ne le ferme pas.
- Si le firmware exécutable et la flash de ressources partagent le message.
- Le numéro d'event de `setFlashDataChunks` : il n'est pas dans le journal, et
  il n'entre pas dans la liste blanche de `tools/wolfmix.py`.

Publié le 2026-08-31, avant toute capture. Aucun octet n'est parti vers
l'appareil pour l'écrire.
