# Inventario del padre r575 — 23 de septiembre de 2026

Corte `b73c33aa761dac418472fa85c7e0985dc98abb73`; base común `30837660a75e4beef5a38f37bf95809edf055f53`; fork revisado `96ebd8ab620e232f6281ddfb2425d152e0334112`.

255 commits no alcanzables desde el fork: 181 cambios y 74 merges. De ellos, 168 llegaron después de la última lectura `7851f67cc`.

Este inventario enumera todo el rango. Los títulos son los originales del autor; no certifican comportamiento. Las decisiones y el alcance de la auditoría están en [el informe](AA10UpstreamReview20260923_es.md). El [JSON](AA10UpstreamReview20260923.json) incluye todos los archivos de cada commit.

## Entregas en la línea principal del padre

| Commit | Entrega original |
|---|---|
| [710e0633f](https://github.com/AAEmu/AAEmu/commit/710e0633f0445e70781405dde5371321c4e9edf0) | Merge pull request #1619 from Razymex/fix/persistence-gate-nested-defer |
| [648203388](https://github.com/AAEmu/AAEmu/commit/648203388a3f023eab7a195c66356521d564c291) | Merge pull request #1625 from Razymex/feat/indun-channel-select |
| [ef377c310](https://github.com/AAEmu/AAEmu/commit/ef377c3107a536e3db4ef72c6bca510bd910dcaa) | Merge pull request #1626 from Razymex/chore/reverse-cleanup |
| [cb60376fa](https://github.com/AAEmu/AAEmu/commit/cb60376fa4355426b4538e18ccc9fd3ecbe0db91) | Merge pull request #1622 from Razymex/feat/achievements |
| [04d800e13](https://github.com/AAEmu/AAEmu/commit/04d800e13aad0c728021daad8186d8e7ce72cf15) | Merge pull request #1628 from Wingsjuankaa/contrib/r575-tax-mail-escaping |
| [418fcc112](https://github.com/AAEmu/AAEmu/commit/418fcc1122f9cceb48ac9048272f3b9001003761) | Merge pull request #1629 from Wingsjuankaa/contrib/r575-script-reload |
| [bd38a3bd5](https://github.com/AAEmu/AAEmu/commit/bd38a3bd5d7439137c9dbeef7804d599c52b1a30) | Merge pull request #1634 from Wingsjuankaa/contrib/r575-npc-remove |
| [5490a8a7c](https://github.com/AAEmu/AAEmu/commit/5490a8a7c3ae19023d8ce57fec51dc4be7263171) | Merge pull request #1616 from Razymex/feat/mate-equip-packs |
| [e59402427](https://github.com/AAEmu/AAEmu/commit/e59402427f93bfb370800f7b0408f5c8261340db) | Merge pull request #1630 from Wingsjuankaa/contrib/r575-item-stack-deltas |
| [ab6faafe1](https://github.com/AAEmu/AAEmu/commit/ab6faafe164c6f9014eb30218dd692378f5b396f) | Merge pull request #1631 from Wingsjuankaa/contrib/r575-sport-fish-loot |
| [cec4c8c66](https://github.com/AAEmu/AAEmu/commit/cec4c8c66e17e66db032029b92742f07b5f22d3f) | Merge pull request #1635 from NL0bP/codex/fix-aaemu-game-sql-import |
| [6707edcd4](https://github.com/AAEmu/AAEmu/commit/6707edcd4f498c764986a95ed3c507f14aac84da) | Merge pull request #1632 from Wingsjuankaa/contrib/r575-zone-buff-snapshot |
| [7df6a4ea3](https://github.com/AAEmu/AAEmu/commit/7df6a4ea3bf149a8aa94a7af1b0481c4ce860790) | Merge pull request #1636 from NL0bP/codex/fix-world-server-launcher |
| [d6c950028](https://github.com/AAEmu/AAEmu/commit/d6c95002885724565e68882852a8f44c9b613357) | Merge pull request #1637 from NL0bP/codex/bump-zone-version-10.0.2.13 |
| [0a669b0c6](https://github.com/AAEmu/AAEmu/commit/0a669b0c6f8e6027b2b0a6cf8028eca4628c13e5) | Merge pull request #1623 from Razymex/feat/achievement-rewards |
| [253d7b3ac](https://github.com/AAEmu/AAEmu/commit/253d7b3aca0e76cb3c6dcb648f34872df4380a20) | Merge pull request #1601 from Razymex/feat/equip-slot-reinforcement |
| [9fa2c3896](https://github.com/AAEmu/AAEmu/commit/9fa2c3896439dd44afb2823850ca73bd6a434bca) | Merge pull request #1638 from NL0bP/codex/fix-nuget-vulnerabilities |
| [7851f67cc](https://github.com/AAEmu/AAEmu/commit/7851f67cc0c46fb76b4fafc3414b6754685d96f2) | Merge pull request #1624 from Razymex/feat/achievement-back-credit |
| [a359b0aad](https://github.com/AAEmu/AAEmu/commit/a359b0aad2ffc9b3af44d4bfaf9143bc4b8becf1) | Merge pull request #1633 from Wingsjuankaa/contrib/r575-squad-login |
| [fae0473a1](https://github.com/AAEmu/AAEmu/commit/fae0473a18e21ff1e705f94b2b4cd77ea6874f87) | Merge pull request #1642 from Razymex/bugfix/off-ground-idle-stand |
| [4e73cd43a](https://github.com/AAEmu/AAEmu/commit/4e73cd43ae074b5737a2034854ac54aa2db1d367) | Merge pull request #1643 from Razymex/bugfix/mobilization-order-accept |
| [d7a8bd2e9](https://github.com/AAEmu/AAEmu/commit/d7a8bd2e90a8b9ed47ceb592b7ce2b9ee7bb9cb7) | Merge pull request #1640 from Vilemouse/aoce-vender-fixes |
| [bad83c4e5](https://github.com/AAEmu/AAEmu/commit/bad83c4e55ff3f210ee78caca96c48cbbd18e7f5) | Merge pull request #1641 from Razymex/feat/craft-order-wire |
| [e2f3f76b7](https://github.com/AAEmu/AAEmu/commit/e2f3f76b7b76b79897ecf9781f6342e457f9df3b) | Merge pull request #1644 from Razymex/bugfix/boat-summon-seed |
| [c7caaa58e](https://github.com/AAEmu/AAEmu/commit/c7caaa58e087418a8aa40d4677b9e08708dea4b7) | Merge pull request #1646 from NickMesser/codex/dynamic-weather |
| [6386a74c2](https://github.com/AAEmu/AAEmu/commit/6386a74c27a438e579f5eabe888c6f57b8e59c4d) | Merge pull request #1645 from Razymex/feat/npc-interaction-sets |
| [d2c2caa0a](https://github.com/AAEmu/AAEmu/commit/d2c2caa0a3eda147ec875fd0552ae06ef4554d72) | Merge pull request #1648 from NickMesser/codex/mentoring-system |
| [7ba04c21b](https://github.com/AAEmu/AAEmu/commit/7ba04c21bbfed6326ead205f7c3f5c01879d1734) | Merge pull request #1647 from Razymex/bugfix/rank-gear-bare-value |
| [a80bbd0ff](https://github.com/AAEmu/AAEmu/commit/a80bbd0ff94be2636c65e1cb81f7d9ccd48a1377) | Merge pull request #1650 from NickMesser/fix/conflict-zone-escalation |
| [ffd01842c](https://github.com/AAEmu/AAEmu/commit/ffd01842c608d81bbfc21e3c4d01099b422355c1) | Merge pull request #1652 from NickMesser/feat/server-owned-special-effects |
| [c61f9772f](https://github.com/AAEmu/AAEmu/commit/c61f9772f2cda873132905c9e286eb6fd2367dae) | Merge pull request #1656 from NickMesser/feat/unit-req-operators |
| [7f7ad0321](https://github.com/AAEmu/AAEmu/commit/7f7ad032176e8289f846e1c44f668e37b9e9e1aa) | Merge pull request #1662 from NickMesser/feat/quest-start-requirements |
| [bfa214e11](https://github.com/AAEmu/AAEmu/commit/bfa214e110d897838d4ee2971184b8bd1d7ac657) | Merge pull request #1666 from NickMesser/codex/wave2-gf-w05 |
| [a5e70afec](https://github.com/AAEmu/AAEmu/commit/a5e70afece8d3c5e5de36fbdbef589ece418cec3) | Merge pull request #1668 from NickMesser/codex/wave2-gf-q06 |
| [809505d3b](https://github.com/AAEmu/AAEmu/commit/809505d3bde35d1fcc9f7dbedb80eaa5198d8360) | Merge pull request #1669 from NickMesser/codex/wave2-gf-q09 |
| [4b4eee2ab](https://github.com/AAEmu/AAEmu/commit/4b4eee2aba2e4a2a5dd1c2d3471034aaa278467a) | Merge pull request #1671 from NickMesser/codex/wave2-gf-q10 |
| [f602aac4e](https://github.com/AAEmu/AAEmu/commit/f602aac4eec67ec687ff52b69cc85ab95b3842d7) | Merge pull request #1674 from NickMesser/codex/wave2-gf-w11 |
| [15756b6b2](https://github.com/AAEmu/AAEmu/commit/15756b6b2bba41c242c7cf19dcf858508e8464ae) | Merge pull request #1665 from NickMesser/codex/gunslinger-targets-reversal |
| [244c7c370](https://github.com/AAEmu/AAEmu/commit/244c7c3705cabbc4073bf7a65896a07d4c23e318) | Merge pull request #1653 from NickMesser/fix/craft-order-followups |
| [d81d661db](https://github.com/AAEmu/AAEmu/commit/d81d661dbc7e77d2d775881914d0ef95ef596973) | Merge pull request #1658 from NickMesser/feat/faction-diplomacy |
| [3bb97971a](https://github.com/AAEmu/AAEmu/commit/3bb97971adc3e0fc5319f49b27013e10a3bc5678) | Merge pull request #1651 from NickMesser/fix/skill-result-mapping |
| [28814fbd4](https://github.com/AAEmu/AAEmu/commit/28814fbd45f064f3ded345afb83404efde4aafce) | Merge pull request #1661 from NickMesser/fix/starter-quest-actors |
| [32981d4a0](https://github.com/AAEmu/AAEmu/commit/32981d4a0364bc942f6777f8ec915c88d51907b8) | Merge pull request #1672 from NickMesser/codex/wave2-gf-w06 |
| [0ef51830f](https://github.com/AAEmu/AAEmu/commit/0ef51830f9525ed5a4f5b5c0aa9a300cda4e66e1) | Merge pull request #1655 from NickMesser/feat/skill-target-semantics |
| [0ad3cf2ce](https://github.com/AAEmu/AAEmu/commit/0ad3cf2ce9f7fc44d0defeade00a736b61050fbe) | Update README with AAEmu 10.x setup link |
| [9242f7cb1](https://github.com/AAEmu/AAEmu/commit/9242f7cb132ef0b5db7e7d59ab46a468161aabf7) | Merge pull request #1657 from NickMesser/feat/quest-progress-acts |
| [b87d2d225](https://github.com/AAEmu/AAEmu/commit/b87d2d22575f9198b816f49b4628a39e4f9d82ef) | Merge pull request #1654 from NickMesser/feat/indun-actions-events-rounds |
| [d6aadd485](https://github.com/AAEmu/AAEmu/commit/d6aadd48533384e0b601381cec709472a3fb9a4c) | Merge pull request #1675 from NickMesser/codex/wave2-gf-q08 |
| [165c59104](https://github.com/AAEmu/AAEmu/commit/165c5910490d397765f69c23a5fc907d3f8c7183) | Merge pull request #1664 from NickMesser/feat/quest-remaining-acts |
| [57b7cf093](https://github.com/AAEmu/AAEmu/commit/57b7cf0933cc723cf3cfa0216dc648c308bbf0c2) | Merge pull request #1660 from NickMesser/feat/raid-recruitment |
| [156f1ac6f](https://github.com/AAEmu/AAEmu/commit/156f1ac6f72fa4e0bd0a326c8325ddc4184f9658) | Merge pull request #1673 from NickMesser/codex/wave2-gf-s02 |
| [ac4e243a2](https://github.com/AAEmu/AAEmu/commit/ac4e243a29ef0f6ceb8f7a50141012e6f6a96282) | Merge pull request #1663 from NickMesser/feat/character-edit-beauty |
| [e586d1556](https://github.com/AAEmu/AAEmu/commit/e586d1556b9375c6a8bbd9c6ca9c78f7a168d56b) | Merge pull request #1667 from NickMesser/codex/wave2-gf-s04 |
| [76d25d1c4](https://github.com/AAEmu/AAEmu/commit/76d25d1c4998398ec0ecce32846fd6c3e991db88) | Merge pull request #1649 from NickMesser/feat/item-proc-events |
| [3ff6ec31a](https://github.com/AAEmu/AAEmu/commit/3ff6ec31ae7244650d094f4376276975de6ebbc0) | Merge pull request #1670 from NickMesser/codex/wave2-gf-w02 |
| [f89c7ea8e](https://github.com/AAEmu/AAEmu/commit/f89c7ea8e8cce9f39b4be9f490d0e904fe402ba6) | Merge pull request #1676 from NickMesser/codex/wave2-gf-s07 |
| [93ed326a1](https://github.com/AAEmu/AAEmu/commit/93ed326a1d0bdfc170f34b9e488fb6912286a22d) | Merge pull request #1677 from NickMesser/codex/fix-null-customization-body-part |
| [e5baa70f3](https://github.com/AAEmu/AAEmu/commit/e5baa70f39b7ec6e5375d598fd46ba9eb8cc7ac6) | Merge pull request #1682 from Razymex/feat/weather-rain-wind |
| [83e9e4480](https://github.com/AAEmu/AAEmu/commit/83e9e4480264a797e0edbffe71be71b2beeb6f82) | Merge pull request #1681 from Razymex/feat/mail-edge-protocols |
| [2da574078](https://github.com/AAEmu/AAEmu/commit/2da57407816ef7830f3d883b8aa4e2ead92e30c4) | Merge pull request #1680 from Razymex/feat/ucc-integrity-apply |
| [94fe6dc13](https://github.com/AAEmu/AAEmu/commit/94fe6dc13f09d0e559017f94b379446f66c90746) | Merge pull request #1678 from Razymex/feat/housing-trade-sale |
| [e20cb8269](https://github.com/AAEmu/AAEmu/commit/e20cb8269cf4a76647c6bae0005c0eec2c75a31b) | Merge pull request #1679 from Razymex/feat/collections-encyclopedia |
| [043c10c58](https://github.com/AAEmu/AAEmu/commit/043c10c58fb8cbaf50e4d8fa3862c7ea707daa31) | Merge pull request #1688 from Razymex/bugfix/housing-trade-followups |
| [c9f9c8d8a](https://github.com/AAEmu/AAEmu/commit/c9f9c8d8ab349af780cdd121d486b79ff3bbb7dc) | Merge pull request #1684 from Razymex/feat/zone-permission-instance-controls |
| [b64bf5be2](https://github.com/AAEmu/AAEmu/commit/b64bf5be297939614c469dd0ad599534401d2a74) | Merge pull request #1690 from Razymex/feat/solo-music-instruments |
| [7424d7960](https://github.com/AAEmu/AAEmu/commit/7424d79601309a767173e126a7e628def6af742c) | Merge pull request #1683 from Razymex/feat/saga-group-progression |
| [c4da6d31f](https://github.com/AAEmu/AAEmu/commit/c4da6d31f2435e84be91b4ad8d3369f42511e81c) | Merge pull request #1687 from Razymex/feat/housing-ucc-plot-geometry |
| [e500b1d76](https://github.com/AAEmu/AAEmu/commit/e500b1d76bd1731a7b1c89d6c0559f2273da46f4) | Merge pull request #1692 from Razymex/feat/local-development-resident |
| [f2282e590](https://github.com/AAEmu/AAEmu/commit/f2282e590165b31ed3935f34a2f04e0936a438ed) | Merge pull request #1693 from Razymex/feat/random-merchants |
| [b73c33aa7](https://github.com/AAEmu/AAEmu/commit/b73c33aa761dac418472fa85c7e0985dc98abb73) | Merge pull request #1698 from Razymex/bugfix/heir-skill-activate |

## Todos los commits pendientes

“Anterior” significa ya presente en la referencia leída anteriormente, no integrado automáticamente en el fork. El número de archivos compara cada commit con su primer padre; no debe sumarse como tamaño neto.

| Commit | Fecha del autor | Lectura | Tipo | Archivos | Descripción original |
|---|---|---|---|---:|---|
| [1d4c190d2](https://github.com/AAEmu/AAEmu/commit/1d4c190d20f499fd98dabacfa3d06675dbf461d4) | 2026-09-17 | Anterior | Cambio | 5 | feat(achievements): store per-character record and achievement progress |
| [582aafc7c](https://github.com/AAEmu/AAEmu/commit/582aafc7c14bb859e0467e0850e263d99dfa2a2e) | 2026-09-17 | Anterior | Cambio | 12 | feat(achievements): evaluate progress from records and push the list |
| [c7dab424c](https://github.com/AAEmu/AAEmu/commit/c7dab424c83b77e220dbd38abfcf884436f643f4) | 2026-09-17 | Anterior | Cambio | 1 | fix(achievements): answer emptily before the content is loaded |
| [c4b4e9e55](https://github.com/AAEmu/AAEmu/commit/c4b4e9e5553068ed7b55b37fee4d21febd94e30a) | 2026-09-18 | Anterior | Cambio | 3 | fix(achievements): let a failed progress write fail the save |
| [ed31fb0bb](https://github.com/AAEmu/AAEmu/commit/ed31fb0bbb2be5e018250e09cefccfb90cd18c34) | 2026-09-18 | Anterior | Cambio | 2 | fix(achievements): look at a watcher again when its child completes later |
| [04b610a1a](https://github.com/AAEmu/AAEmu/commit/04b610a1a12532bfa0e0467babe4320bc57c4283) | 2026-09-18 | Anterior | Cambio | 2 | fix(achievements): make a reset clear the records it is judged by |
| [2f735856c](https://github.com/AAEmu/AAEmu/commit/2f735856ccb35e799161455ca013a24df78d8ee1) | 2026-09-18 | Anterior | Cambio | 1 | fix(achievements): correct the complete_num the comment quotes |
| [12ea7cb17](https://github.com/AAEmu/AAEmu/commit/12ea7cb17cf83e8ee3f06eb4163a6ddfe4070cfd) | 2026-09-17 | Anterior | Cambio | 6 | feat(achievements): pay rewards, complete sub-categories, skip what the season switched off |
| [d123b45a7](https://github.com/AAEmu/AAEmu/commit/d123b45a721f379448c13b6a353812a906fdfa2d) | 2026-09-17 | Anterior | Cambio | 3 | feat(achievements): credit what an earned achievement pre-completes |
| [7ebca853f](https://github.com/AAEmu/AAEmu/commit/7ebca853fcc037d961b4ff2847b4fbbab51d0079) | 2026-09-18 | Anterior | Cambio | 12 | feat(indun): offer the channel picker and honour the dimension that is picked |
| [1ba1cd082](https://github.com/AAEmu/AAEmu/commit/1ba1cd0823ff92bdfd4fd68f1955fcc61a79fcfa) | 2026-09-18 | Anterior | Cambio | 5 | fix(indun): offer only the dimension copies a host is serving |
| [b9b39d5ba](https://github.com/AAEmu/AAEmu/commit/b9b39d5ba79e850ef56c43057c2acdd131ed4886) | 2026-09-18 | Anterior | Cambio | 6 | fix(indun): keep a picked dimension to its own instance and its own entry |
| [9fb684007](https://github.com/AAEmu/AAEmu/commit/9fb6840076948cf0350d4f344a1c25dd91b4fd56) | 2026-09-17 | Anterior | Cambio | 3 | fix(persistence): keep the operation gate balanced when the layers meet |
| [c080027c7](https://github.com/AAEmu/AAEmu/commit/c080027c75c1abe106f241ec2fdf8af963294e1c) | 2026-09-17 | Anterior | Cambio | 1 | fix(persistence): a mail flush must not recurse into the save that called it |
| [46d6e3376](https://github.com/AAEmu/AAEmu/commit/46d6e3376288be4193d4b6d76e4410e153cd9ffe) | 2026-09-18 | Anterior | Cambio | 1 | test(persistence): keep the gate tests off the lock while they assert |
| [eb641903f](https://github.com/AAEmu/AAEmu/commit/eb641903f06277c529906e539f923b1fe87dd3bd) | 2026-09-18 | Anterior | Cambio | 1 | test(persistence): cover the deferral under a held gate and the re-entrant flush |
| [94ba1034d](https://github.com/AAEmu/AAEmu/commit/94ba1034db192bc8e767b73cf629eb46e8fb27c8) | 2026-09-18 | Anterior | Cambio | 4 | docs: drop provenance notes from the family/guild, chat and synthesis docs |
| [3b48fb49a](https://github.com/AAEmu/AAEmu/commit/3b48fb49a57f49a45974141e5653c633456015de) | 2026-09-18 | Anterior | Cambio | 20 | chore(butlers): drop provenance comments from butler and item wire code |
| [377891b21](https://github.com/AAEmu/AAEmu/commit/377891b213554c3bed2d7ade9dd68c1167aabb67) | 2026-09-18 | Anterior | Cambio | 16 | chore(duels): drop provenance comments from duel and team packets |
| [fa2f6b053](https://github.com/AAEmu/AAEmu/commit/fa2f6b053a3c38b269c56c928570af383bf3c149) | 2026-09-18 | Anterior | Cambio | 15 | chore(characters): drop provenance comments from character and mail code |
| [d3924072e](https://github.com/AAEmu/AAEmu/commit/d3924072ebbc14b772ff05e01b2f1701600b0867) | 2026-09-18 | Anterior | Cambio | 44 | chore(packets): drop provenance comments from resident, chat and world packets |
| [31583f844](https://github.com/AAEmu/AAEmu/commit/31583f8448db6e9303af75849566be41f29715b4) | 2026-09-17 | Anterior | Cambio | 4 | feat(slaves): take a piece into a mate's slot only when its kind fits there |
| [3cf288622](https://github.com/AAEmu/AAEmu/commit/3cf288622fb759daaa7aff37de59fb1c22a1eb00) | 2026-09-17 | Anterior | Cambio | 5 | fix(slaves): the kinds table is a ship's, and a mate wears what its packs list |
| [0c3875655](https://github.com/AAEmu/AAEmu/commit/0c3875655be59dafc8111eb0c07469d4b5f8a92b) | 2026-09-17 | Anterior | Cambio | 3 | feat(slaves): a mate also only wears the positions its own kind has |
| [75a9b31ab](https://github.com/AAEmu/AAEmu/commit/75a9b31ab623d9d7bad90848afe5a7edf112ace7) | 2026-09-17 | Anterior | Cambio | 4 | feat(slaves): a ship only uses the equipment packs it is allowed |
| [3786c0483](https://github.com/AAEmu/AAEmu/commit/3786c048301e6bc156b3ada877ebdacc27c6075c) | 2026-09-16 | Anterior | Cambio | 9 | feat(items): load the equip slot reinforcement ladders and their wire |
| [24c528f91](https://github.com/AAEmu/AAEmu/commit/24c528f91cb0db3e62f3635b714ea77cb02427ff) | 2026-09-16 | Anterior | Cambio | 9 | feat(items): track a character's equip slot reinforcement progress |
| [2a885a409](https://github.com/AAEmu/AAEmu/commit/2a885a40944af888010218dd213e92f6afc01e80) | 2026-09-16 | Anterior | Cambio | 2 | feat(items): give the reinforcement ladders a GM surface |
| [8a778419c](https://github.com/AAEmu/AAEmu/commit/8a778419cedca381f80a850c8152eda7649ead43) | 2026-09-16 | Anterior | Cambio | 3 | feat(items): carry equip slot reinforcement in the unit state |
| [cc1354d58](https://github.com/AAEmu/AAEmu/commit/cc1354d58b158c8acdc3f870334603473f5eee96) | 2026-09-16 | Anterior | Cambio | 1 | fix(items): send the reinforcement level the client actually indexes |
| [71fe796c4](https://github.com/AAEmu/AAEmu/commit/71fe796c4372efd3038c3f510da45e003c0267eb) | 2026-09-16 | Anterior | Cambio | 3 | feat(items): feed a reinforcement slot from its material set |
| [c96792a15](https://github.com/AAEmu/AAEmu/commit/c96792a152a8202fd1772fcb71d991ffefe1e66e) | 2026-09-18 | Anterior | Cambio | 16 | feat(items): let the artifact window drive its tier effects |
| [23bd1520a](https://github.com/AAEmu/AAEmu/commit/23bd1520a3d87dee6244737e5a0d46b4f373b408) | 2026-09-18 | Anterior | Cambio | 1 | fix(items): read the artifact replace price from the content config |
| [3ba20c796](https://github.com/AAEmu/AAEmu/commit/3ba20c796ade48d39406e7d2c4c64568a8e43391) | 2026-09-18 | Anterior | Cambio | 2 | fix(mail): escape housing names in tax mail Lua arguments |
| [1aa753200](https://github.com/AAEmu/AAEmu/commit/1aa7532009a8ed7c6abd40adbeb74a6e3b9127c2) | 2026-09-18 | Anterior | Cambio | 4 | fix(scripts): retain commands when reload compilation fails |
| [b5142be8f](https://github.com/AAEmu/AAEmu/commit/b5142be8f687e6b2a30c31f9cb7e65792e058f68) | 2026-09-18 | Anterior | Cambio | 6 | fix(items): report acquired and consumed stack deltas |
| [325272189](https://github.com/AAEmu/AAEmu/commit/325272189a440ef6394e4ebc91be5f27b9339576) | 2026-09-18 | Anterior | Cambio | 3 | fix(loot): equip caught fish when the bag is full |
| [7b9a74d4d](https://github.com/AAEmu/AAEmu/commit/7b9a74d4d85430c08f33f1827bfbdb9c7eaaac30) | 2026-09-18 | Anterior | Cambio | 6 | fix(world): track buffs delivered in initial unit snapshots |
| [db59558b6](https://github.com/AAEmu/AAEmu/commit/db59558b6181749ad105322cd62d15b5d78b9dd0) | 2026-09-18 | Nueva | Cambio | 2 | fix(squads): avoid false disband notifications on login |
| [4e480846b](https://github.com/AAEmu/AAEmu/commit/4e480846ba43d693098a1ec28d474de864423aea) | 2026-09-18 | Anterior | Cambio | 1 | fix(commands): handle NPC removal without a spawner |
| [a69838a03](https://github.com/AAEmu/AAEmu/commit/a69838a036174be62bc140f68e797de4826e56b8) | 2026-09-18 | Anterior | Cambio | 3 | chore(packets): drop leftover reverse offsets from initial-config notes |
| [00a0eb27d](https://github.com/AAEmu/AAEmu/commit/00a0eb27d4b5dd6fe3cea46183af169cb13a240e) | 2026-09-18 | Anterior | Cambio | 2 | fix(mail): FlushRequestedNow must not release a lock the deferral did not take |
| [14aad4cfb](https://github.com/AAEmu/AAEmu/commit/14aad4cfb581da0498c07484103c071e98461e9d) | 2026-09-18 | Anterior | Cambio | 3 | fix(indun): honour a channel pick only when SelectChannel and treat a missing host as hosted |
| [db61e3e3f](https://github.com/AAEmu/AAEmu/commit/db61e3e3ff01a7865d5834e739a80cbe21a5f633) | 2026-09-18 | Anterior | Cambio | 7 | fix(items): map mate slots by EquipmentItemSlot and keep group-kind ship positions open |
| [fbc5e32ce](https://github.com/AAEmu/AAEmu/commit/fbc5e32ce89914b82a66f8595e6f0dda2853ee7c) | 2026-09-18 | Anterior | Cambio | 4 | fix(items): gate a reinforce feed on skill 38363 and exclude the current row from a reroll |
| [53db2c54a](https://github.com/AAEmu/AAEmu/commit/53db2c54aa48c596a8b6c2d3fffc3468bb026a66) | 2026-09-18 | Anterior | Cambio | 3 | fix(achievements): skip no-objective members when a sub-category pays |
| [e5fa2b10c](https://github.com/AAEmu/AAEmu/commit/e5fa2b10ca53857b6fdfe6c9776b84acc99a404d) | 2026-09-18 | Anterior | Cambio | 3 | fix(achievements): keep a still-complete child's completion record on reset |
| [58d2908e7](https://github.com/AAEmu/AAEmu/commit/58d2908e7d7ea39afaa5ea813038d247dd02de42) | 2026-09-18 | Anterior | Cambio | 5 | fix(achievements): treat pre_completed_achievements as a prerequisite gate |
| [8efd02576](https://github.com/AAEmu/AAEmu/commit/8efd0257621df342d0d33c2a873e2c7bf3732cdc) | 2026-09-18 | Anterior | Cambio | 1 | fix(sql): sync game updates into aaemu dump |
| [c6950a3a4](https://github.com/AAEmu/AAEmu/commit/c6950a3a416614623c899cd3e9b65e0cb3a4ab3d) | 2026-09-18 | Anterior | Merge | 3 | merge feat/achievements into feat/achievement-rewards |
| [ba058cb34](https://github.com/AAEmu/AAEmu/commit/ba058cb3490ae2dcefcd1b2041e68b635718e35c) | 2026-09-18 | Anterior | Merge | 4 | merge feat/achievement-rewards into feat/achievement-back-credit |
| [710e0633f](https://github.com/AAEmu/AAEmu/commit/710e0633f0445e70781405dde5371321c4e9edf0) | 2026-09-18 | Anterior | Merge | 4 | Merge pull request #1619 from Razymex/fix/persistence-gate-nested-defer |
| [648203388](https://github.com/AAEmu/AAEmu/commit/648203388a3f023eab7a195c66356521d564c291) | 2026-09-18 | Anterior | Merge | 12 | Merge pull request #1625 from Razymex/feat/indun-channel-select |
| [ef377c310](https://github.com/AAEmu/AAEmu/commit/ef377c3107a536e3db4ef72c6bca510bd910dcaa) | 2026-09-18 | Anterior | Merge | 101 | Merge pull request #1626 from Razymex/chore/reverse-cleanup |
| [cb60376fa](https://github.com/AAEmu/AAEmu/commit/cb60376fa4355426b4538e18ccc9fd3ecbe0db91) | 2026-09-18 | Anterior | Merge | 15 | Merge pull request #1622 from Razymex/feat/achievements |
| [91c6d96dd](https://github.com/AAEmu/AAEmu/commit/91c6d96dd02af1e8b814d80b9ce0cd490dda21fa) | 2026-09-18 | Anterior | Cambio | 3 | fix(achievements): re-evaluate gated achievements when a prerequisite completes |
| [9032e423c](https://github.com/AAEmu/AAEmu/commit/9032e423c3dbc9d7ec530339cd1703d58b097076) | 2026-09-18 | Anterior | Cambio | 3 | fix(slaves): skip a starter part whose item template does not exist |
| [09f8eb3ee](https://github.com/AAEmu/AAEmu/commit/09f8eb3eef695657735b83ff2a8c6565cb230d3a) | 2026-09-18 | Anterior | Cambio | 4 | fix(items): treat a need_exp 0 row as the reinforce cap and charge the feed gold |
| [a60fc3b67](https://github.com/AAEmu/AAEmu/commit/a60fc3b67a1381b2b760e9ad4a9ca5f14e98b90c) | 2026-09-18 | Anterior | Cambio | 1 | fix(sql): remove obsolete cash shop table |
| [04d800e13](https://github.com/AAEmu/AAEmu/commit/04d800e13aad0c728021daad8186d8e7ce72cf15) | 2026-09-18 | Anterior | Merge | 2 | Merge pull request #1628 from Wingsjuankaa/contrib/r575-tax-mail-escaping |
| [418fcc112](https://github.com/AAEmu/AAEmu/commit/418fcc1122f9cceb48ac9048272f3b9001003761) | 2026-09-18 | Anterior | Merge | 4 | Merge pull request #1629 from Wingsjuankaa/contrib/r575-script-reload |
| [bd38a3bd5](https://github.com/AAEmu/AAEmu/commit/bd38a3bd5d7439137c9dbeef7804d599c52b1a30) | 2026-09-18 | Anterior | Merge | 1 | Merge pull request #1634 from Wingsjuankaa/contrib/r575-npc-remove |
| [a92beaa0d](https://github.com/AAEmu/AAEmu/commit/a92beaa0d0c36e446c97bdfb44b1df0f2636daa7) | 2026-09-18 | Anterior | Cambio | 8 | fix(items): stop completed stack acquisition and retain frozen deltas |
| [76f6530c2](https://github.com/AAEmu/AAEmu/commit/76f6530c283322cc1a0daf559b0b43fa929177d0) | 2026-09-18 | Anterior | Cambio | 2 | fix(loot): restrict backpack auto-equip to single-item drops |
| [5490a8a7c](https://github.com/AAEmu/AAEmu/commit/5490a8a7c3ae19023d8ce57fec51dc4be7263171) | 2026-09-18 | Anterior | Merge | 11 | Merge pull request #1616 from Razymex/feat/mate-equip-packs |
| [e59402427](https://github.com/AAEmu/AAEmu/commit/e59402427f93bfb370800f7b0408f5c8261340db) | 2026-09-18 | Anterior | Merge | 4 | Merge pull request #1630 from Wingsjuankaa/contrib/r575-item-stack-deltas |
| [ab6faafe1](https://github.com/AAEmu/AAEmu/commit/ab6faafe164c6f9014eb30218dd692378f5b396f) | 2026-09-18 | Anterior | Merge | 3 | Merge pull request #1631 from Wingsjuankaa/contrib/r575-sport-fish-loot |
| [ab2257520](https://github.com/AAEmu/AAEmu/commit/ab225752002d162fc2c4b1e41d591a8817b8f383) | 2026-09-18 | Anterior | Merge | 136 | Merge branch 'client_version/zone-10.0.2_r575' into codex/fix-aaemu-game-sql-import |
| [c3d48b4ae](https://github.com/AAEmu/AAEmu/commit/c3d48b4ae00c28e8cdf8beda59f80dd06ddb7566) | 2026-09-18 | Anterior | Cambio | 3 | fix(achievements): keep a still-complete sub-category record on reset |
| [932ed4271](https://github.com/AAEmu/AAEmu/commit/932ed4271d3e5cbb43d3024d5bf7824cac0e50d1) | 2026-09-18 | Anterior | Cambio | 3 | fix(items): count reinforce materials in the bag and refund gold if consume fails |
| [0bbc9cbc8](https://github.com/AAEmu/AAEmu/commit/0bbc9cbc832091da764f44dbe062e5e9400bb0d3) | 2026-09-18 | Anterior | Merge | 3 | merge feat/achievement-rewards into feat/achievement-back-credit |
| [cec4c8c66](https://github.com/AAEmu/AAEmu/commit/cec4c8c66e17e66db032029b92742f07b5f22d3f) | 2026-09-18 | Anterior | Merge | 1 | Merge pull request #1635 from NL0bP/codex/fix-aaemu-game-sql-import |
| [77bab536b](https://github.com/AAEmu/AAEmu/commit/77bab536b8e06a059c2744d2d562e00a66812b90) | 2026-09-18 | Anterior | Cambio | 4 | fix(world): respect buff authority when retiring snapshots |
| [477a8f681](https://github.com/AAEmu/AAEmu/commit/477a8f681ccb5ce23e85255cb93b0f7ad37c4932) | 2026-09-18 | Anterior | Cambio | 3 | fix(scripts): add World server launch scripts |
| [e3bb46164](https://github.com/AAEmu/AAEmu/commit/e3bb461646f1b477f219d06dbbc18bd36f90223a) | 2026-09-18 | Anterior | Cambio | 1 | chore(build): bump zone version to 10.0.2.13 |
| [e48c0026d](https://github.com/AAEmu/AAEmu/commit/e48c0026dd337e73e44d257bb6f10f1265fbc97d) | 2026-09-18 | Anterior | Cambio | 4 | fix(deps): remediate vulnerable NuGet packages |
| [6707edcd4](https://github.com/AAEmu/AAEmu/commit/6707edcd4f498c764986a95ed3c507f14aac84da) | 2026-09-18 | Anterior | Merge | 7 | Merge pull request #1632 from Wingsjuankaa/contrib/r575-zone-buff-snapshot |
| [7df6a4ea3](https://github.com/AAEmu/AAEmu/commit/7df6a4ea3bf149a8aa94a7af1b0481c4ce860790) | 2026-09-18 | Anterior | Merge | 3 | Merge pull request #1636 from NL0bP/codex/fix-world-server-launcher |
| [d6c950028](https://github.com/AAEmu/AAEmu/commit/d6c95002885724565e68882852a8f44c9b613357) | 2026-09-18 | Anterior | Merge | 1 | Merge pull request #1637 from NL0bP/codex/bump-zone-version-10.0.2.13 |
| [b35be3d18](https://github.com/AAEmu/AAEmu/commit/b35be3d1849c1d473578a3103ed2319b32c9dc28) | 2026-09-19 | Anterior | Cambio | 1 | fix(deps): use stable SQLitePCLRaw package |
| [8696245d6](https://github.com/AAEmu/AAEmu/commit/8696245d68230c89ff809fd41a28769c96c44a6d) | 2026-09-19 | Anterior | Cambio | 3 | fix(achievements): localize overflow mail through .achievementNew |
| [1fed6fd2c](https://github.com/AAEmu/AAEmu/commit/1fed6fd2c1a653480efad2c76e7be050d5ecedd4) | 2026-09-19 | Anterior | Cambio | 3 | fix(items): consume every reinforce set member and refuse below the enable level |
| [1e1102845](https://github.com/AAEmu/AAEmu/commit/1e1102845bf4eed4f5ac11620dd1917cf4cd5937) | 2026-09-19 | Anterior | Merge | 3 | merge feat/achievement-rewards into feat/achievement-back-credit |
| [8449c2455](https://github.com/AAEmu/AAEmu/commit/8449c24558c0a40cd7a92e9a2b18e880032dee53) | 2026-09-19 | Anterior | Cambio | 2 | fix(deps): remove redundant AppHost overrides |
| [0a669b0c6](https://github.com/AAEmu/AAEmu/commit/0a669b0c6f8e6027b2b0a6cf8028eca4628c13e5) | 2026-09-18 | Anterior | Merge | 6 | Merge pull request #1623 from Razymex/feat/achievement-rewards |
| [253d7b3ac](https://github.com/AAEmu/AAEmu/commit/253d7b3aca0e76cb3c6dcb648f34872df4380a20) | 2026-09-18 | Anterior | Merge | 24 | Merge pull request #1601 from Razymex/feat/equip-slot-reinforcement |
| [9fa2c3896](https://github.com/AAEmu/AAEmu/commit/9fa2c3896439dd44afb2823850ca73bd6a434bca) | 2026-09-18 | Anterior | Merge | 4 | Merge pull request #1638 from NL0bP/codex/fix-nuget-vulnerabilities |
| [7851f67cc](https://github.com/AAEmu/AAEmu/commit/7851f67cc0c46fb76b4fafc3414b6754685d96f2) | 2026-09-18 | Anterior | Merge | 5 | Merge pull request #1624 from Razymex/feat/achievement-back-credit |
| [7ddee7b16](https://github.com/AAEmu/AAEmu/commit/7ddee7b16461ede9de07a24bc138cf39a4137886) | 2026-09-18 | Nueva | Cambio | 2 | fix(squads): replay missed disbands on member login |
| [dd3dd6d39](https://github.com/AAEmu/AAEmu/commit/dd3dd6d390d911afbc43c777548ceb77ef48aa73) | 2026-09-19 | Nueva | Cambio | 2 | fix(vendors): stop non-gold vendors from silently rejecting every purchase |
| [9a29aaff7](https://github.com/AAEmu/AAEmu/commit/9a29aaff728026b04253b8dd5bb49c253771b6fe) | 2026-09-20 | Nueva | Cambio | 71 | feat(craft-order): implement the request board, Instant complete, and My List load |
| [2a77d8a57](https://github.com/AAEmu/AAEmu/commit/2a77d8a5784c77aaeace291dab6a36a7e39e29c3) | 2026-09-20 | Nueva | Cambio | 3 | fix(packets): give a changed game point a count and its real kind |
| [e73ddaff2](https://github.com/AAEmu/AAEmu/commit/e73ddaff2143df26730dcb415f2d037607204713) | 2026-09-20 | Nueva | Cambio | 3 | fix(scripts): give the vocation command its own name and an exact amount |
| [fb92e4ec6](https://github.com/AAEmu/AAEmu/commit/fb92e4ec6e2336b36986765f40288fba910ddac7) | 2026-09-20 | Nueva | Cambio | 1 | fix(packets): drop the extra byte from SCGamePointInitedPacket |
| [98828fb41](https://github.com/AAEmu/AAEmu/commit/98828fb41abcd879e40bf03bb62368651dcd1df4) | 2026-09-20 | Nueva | Cambio | 1 | feat(scripts): add a GM honor point command |
| [97c9514f3](https://github.com/AAEmu/AAEmu/commit/97c9514f3a2f2da527c2e61c8935da1c3e42be6d) | 2026-09-20 | Nueva | Cambio | 3 | fix(movement): keep streaming hover stands for off-ground units |
| [fa0c4e71e](https://github.com/AAEmu/AAEmu/commit/fa0c4e71e7d06b619f4738405c6796cafcc5b2b1) | 2026-09-20 | Nueva | Cambio | 15 | fix(hero): land mobilization accept beside the flag and persist the clocks |
| [20af52662](https://github.com/AAEmu/AAEmu/commit/20af52662e935533e13dca898b66079ff34c9e1c) | 2026-09-20 | Nueva | Cambio | 5 | fix(hero): load the live instance on mobilization accept |
| [6f604eda0](https://github.com/AAEmu/AAEmu/commit/6f604eda0a8674d7ea5143cf0cb6009c2e34f04a) | 2026-09-20 | Nueva | Cambio | 8 | fix(game): route remaining teleports through the shared landing |
| [a359b0aad](https://github.com/AAEmu/AAEmu/commit/a359b0aad2ffc9b3af44d4bfaf9143bc4b8becf1) | 2026-09-20 | Nueva | Merge | 3 | Merge pull request #1633 from Wingsjuankaa/contrib/r575-squad-login |
| [fae0473a1](https://github.com/AAEmu/AAEmu/commit/fae0473a18e21ff1e705f94b2b4cd77ea6874f87) | 2026-09-20 | Nueva | Merge | 3 | Merge pull request #1642 from Razymex/bugfix/off-ground-idle-stand |
| [6a8a4a1c7](https://github.com/AAEmu/AAEmu/commit/6a8a4a1c746512576f6bb189622d239237df8d49) | 2026-09-21 | Nueva | Cambio | 9 | fix(hero): pick rally stands by zone pad, not milestone |
| [574973446](https://github.com/AAEmu/AAEmu/commit/574973446a00958359844cc9cf0ab12272ba2700) | 2026-09-21 | Nueva | Cambio | 16 | fix(craft-order): close review gaps on fee, sheet, and board kinds |
| [6c9049b0e](https://github.com/AAEmu/AAEmu/commit/6c9049b0e28aec0f772d9dbb733730c9d4caf234) | 2026-09-21 | Nueva | Cambio | 5 | fix(hero): pick rally stands from level return pads only |
| [36a83c1c1](https://github.com/AAEmu/AAEmu/commit/36a83c1c1dbcc1c7efdafeea509d73aaabbff8f1) | 2026-09-21 | Nueva | Cambio | 5 | fix(gamepoints): name the slots once and bound the GM command arguments |
| [d2fa3b31a](https://github.com/AAEmu/AAEmu/commit/d2fa3b31a2ad8951a3dbb5f4bcb465ec01c2d782) | 2026-09-21 | Nueva | Cambio | 25 | fix(craft-order): match the post floor to the client and stop expire-sweep spin |
| [4e73cd43a](https://github.com/AAEmu/AAEmu/commit/4e73cd43ae074b5737a2034854ac54aa2db1d367) | 2026-09-20 | Nueva | Merge | 27 | Merge pull request #1643 from Razymex/bugfix/mobilization-order-accept |
| [d7a8bd2e9](https://github.com/AAEmu/AAEmu/commit/d7a8bd2e90a8b9ed47ceb592b7ce2b9ee7bb9cb7) | 2026-09-20 | Nueva | Merge | 9 | Merge pull request #1640 from Vilemouse/aoce-vender-fixes |
| [bad83c4e5](https://github.com/AAEmu/AAEmu/commit/bad83c4e55ff3f210ee78caca96c48cbbd18e7f5) | 2026-09-20 | Nueva | Merge | 70 | Merge pull request #1641 from Razymex/feat/craft-order-wire |
| [6bcd98981](https://github.com/AAEmu/AAEmu/commit/6bcd989815c8ddf9412165f738d25216fbe76183) | 2026-09-21 | Nueva | Cambio | 5 | fix(slave): plant summons on the client seed |
| [fd3eebeb3](https://github.com/AAEmu/AAEmu/commit/fd3eebeb3a8b16b2e97b06aeb57ba44400ea5a1f) | 2026-09-21 | Nueva | Cambio | 5 | fix(slave): bound the client summon seed |
| [e2f3f76b7](https://github.com/AAEmu/AAEmu/commit/e2f3f76b7b76b79897ecf9781f6342e457f9df3b) | 2026-09-21 | Nueva | Merge | 5 | Merge pull request #1644 from Razymex/bugfix/boat-summon-seed |
| [daf58eb52](https://github.com/AAEmu/AAEmu/commit/daf58eb523d4fa562c052597d5451822a12a9a88) | 2026-09-21 | Nueva | Cambio | 28 | feat(npc): load authored interaction sets and run their plots as the NPC |
| [bc3000155](https://github.com/AAEmu/AAEmu/commit/bc30001558f2a54de4c133795aa825e34d8a9a85) | 2026-09-21 | Nueva | Cambio | 10 | fix(weather): restore native global snow control for 10.x |
| [75a39e914](https://github.com/AAEmu/AAEmu/commit/75a39e914dd9a850254538b3633e341922f8743d) | 2026-09-21 | Nueva | Cambio | 3 | docs(weather): retain verified snow feature flag annotations |
| [80e2c2743](https://github.com/AAEmu/AAEmu/commit/80e2c27430032b0158a0bbd8e1a2d2fad9f53b5f) | 2026-09-21 | Nueva | Cambio | 1 | chore(weather): preserve unrelated feature file formatting |
| [9e5aacbfc](https://github.com/AAEmu/AAEmu/commit/9e5aacbfcfe9338c63f16466222f4f489caf2ced) | 2026-09-21 | Nueva | Cambio | 8 | fix(weather): seed native snow state before client world loading |
| [c7caaa58e](https://github.com/AAEmu/AAEmu/commit/c7caaa58e087418a8aa40d4677b9e08708dea4b7) | 2026-09-21 | Nueva | Merge | 13 | Merge pull request #1646 from NickMesser/codex/dynamic-weather |
| [96b2b813a](https://github.com/AAEmu/AAEmu/commit/96b2b813ae8de7c6eb55cf6e027194ecbd0cdf25) | 2026-09-21 | Nueva | Cambio | 6 | fix(npc): keep interaction plots on the player and count a radius-0 target |
| [6386a74c2](https://github.com/AAEmu/AAEmu/commit/6386a74c27a438e579f5eabe888c6f57b8e59c4d) | 2026-09-21 | Nueva | Merge | 27 | Merge pull request #1645 from Razymex/feat/npc-interaction-sets |
| [54d5524bb](https://github.com/AAEmu/AAEmu/commit/54d5524bb8085130e84305e3fcd0f22dc3ff1f30) | 2026-09-21 | Nueva | Cambio | 18 | feat(mentoring): restore dungeon mentor and mentee quests |
| [df1a450cc](https://github.com/AAEmu/AAEmu/commit/df1a450cc5bca87654e9cd335774fc3f005e4d16) | 2026-09-21 | Nueva | Cambio | 3 | fix(doodads): preserve row-bound FakeUse progression |
| [4c18f7749](https://github.com/AAEmu/AAEmu/commit/4c18f7749dbd7e28dfc9d838b9db374a2dd89f61) | 2026-09-21 | Nueva | Cambio | 8 | fix(zones): count PvP kills before the honor table so conflict zones escalate |
| [6d5639de9](https://github.com/AAEmu/AAEmu/commit/6d5639de9932e0ca8a4a65b1961cf0b5427add96) | 2026-09-21 | Nueva | Cambio | 19 | feat(skills): classify every shipped special effect type and stop charging unsupported casts |
| [5c93f2981](https://github.com/AAEmu/AAEmu/commit/5c93f298180eb41f522cb71ea2d88e363f1b46d1) | 2026-09-21 | Nueva | Cambio | 5 | fix(craft-order): return the sheet on a failed post write and refund every order on a GM wipe |
| [8a9599ce3](https://github.com/AAEmu/AAEmu/commit/8a9599ce37ba80c4a9597f32b60ce7febcbb65ab) | 2026-09-21 | Nueva | Cambio | 11 | feat(units): evaluate the remaining unit_reqs kinds with the client's operators |
| [9067221dd](https://github.com/AAEmu/AAEmu/commit/9067221dd04a54a986461c1770cdc91bcb00eea7) | 2026-09-21 | Nueva | Cambio | 13 | feat(skills): pin the range band, siege offense HQ users and summon targets |
| [097798d01](https://github.com/AAEmu/AAEmu/commit/097798d016507ea330138108f41f19d450d99cc5) | 2026-09-21 | Nueva | Cambio | 40 | feat(quests): implement the missing Progress act types |
| [f8dd4d7b5](https://github.com/AAEmu/AAEmu/commit/f8dd4d7b5060c55dab35b94e86eeeac7d3eb6b86) | 2026-09-21 | Nueva | Cambio | 29 | feat(factions): implement hero diplomacy relations, history and counts |
| [8baeb1a98](https://github.com/AAEmu/AAEmu/commit/8baeb1a98b8d018f368a89d93832a42c60680ab6) | 2026-09-22 | Nueva | Cambio | 1 | test(skills): keep the stop-channeling tests off the parallel runner |
| [a5d0cb50d](https://github.com/AAEmu/AAEmu/commit/a5d0cb50d8053c0eba704357ee80b3f48067e889) | 2026-09-22 | Nueva | Cambio | 10 | feat(quests): answer a refused Start requirement with SCQuestUnitReqFailed |
| [596bcba1e](https://github.com/AAEmu/AAEmu/commit/596bcba1e0821e5c9d1d8f94c3a8f22925bc7c4e) | 2026-09-22 | Nueva | Cambio | 17 | feat(character): implement beauty shop edits and the lobby character edit |
| [362f439f8](https://github.com/AAEmu/AAEmu/commit/362f439f8feb1606f68efabadcde049421500b92) | 2026-09-21 | Nueva | Cambio | 8 | fix(rankings): match the client's gear score on the board |
| [1b8b10f2d](https://github.com/AAEmu/AAEmu/commit/1b8b10f2dbe89ccd3d01ca08890c200ac5b846bb) | 2026-09-22 | Nueva | Cambio | 10 | fix(rankings): refresh the cached gear score and share it with offline siege |
| [2f23c39cd](https://github.com/AAEmu/AAEmu/commit/2f23c39cd1c4c88ac9a006a481abdf7b5411193f) | 2026-09-22 | Nueva | Cambio | 9 | fix(skills): correct plot targets and Reversal debuff transfer |
| [d2c2caa0a](https://github.com/AAEmu/AAEmu/commit/d2c2caa0a3eda147ec875fd0552ae06ef4554d72) | 2026-09-22 | Nueva | Merge | 20 | Merge pull request #1648 from NickMesser/codex/mentoring-system |
| [7ba04c21b](https://github.com/AAEmu/AAEmu/commit/7ba04c21bbfed6326ead205f7c3f5c01879d1734) | 2026-09-22 | Nueva | Merge | 15 | Merge pull request #1647 from Razymex/bugfix/rank-gear-bare-value |
| [a80bbd0ff](https://github.com/AAEmu/AAEmu/commit/a80bbd0ff94be2636c65e1cb81f7d9ccd48a1377) | 2026-09-22 | Nueva | Merge | 8 | Merge pull request #1650 from NickMesser/fix/conflict-zone-escalation |
| [ffd01842c](https://github.com/AAEmu/AAEmu/commit/ffd01842c608d81bbfc21e3c4d01099b422355c1) | 2026-09-22 | Nueva | Merge | 19 | Merge pull request #1652 from NickMesser/feat/server-owned-special-effects |
| [c61f9772f](https://github.com/AAEmu/AAEmu/commit/c61f9772f2cda873132905c9e286eb6fd2367dae) | 2026-09-22 | Nueva | Merge | 11 | Merge pull request #1656 from NickMesser/feat/unit-req-operators |
| [7f7ad0321](https://github.com/AAEmu/AAEmu/commit/7f7ad032176e8289f846e1c44f668e37b9e9e1aa) | 2026-09-22 | Nueva | Merge | 10 | Merge pull request #1662 from NickMesser/feat/quest-start-requirements |
| [b44d4839d](https://github.com/AAEmu/AAEmu/commit/b44d4839d6310875eec94078b47845e80f120950) | 2026-09-22 | Nueva | Cambio | 8 | Implement content-backed guild benefits |
| [8b79b7a60](https://github.com/AAEmu/AAEmu/commit/8b79b7a60be8601522c04a87bfd81d361dc0e7c1) | 2026-09-22 | Nueva | Cambio | 3 | feat(doodads): load build condition UI functions |
| [69be3c074](https://github.com/AAEmu/AAEmu/commit/69be3c074b86d3483c020d0206aa1fef9b4aa118) | 2026-09-22 | Nueva | Cambio | 4 | Implement supported doodad NPC spawns |
| [3e02014a7](https://github.com/AAEmu/AAEmu/commit/3e02014a73f09fad30bb6262a024773d97c78032) | 2026-09-22 | Nueva | Cambio | 5 | feat(zones): apply authored daily war windows |
| [9eb908d18](https://github.com/AAEmu/AAEmu/commit/9eb908d18ecb12662fa73c29d6d87bfe2f6a6e60) | 2026-09-22 | Nueva | Cambio | 6 | feat(doodads): load small UI function descriptors |
| [6bc8d28c3](https://github.com/AAEmu/AAEmu/commit/6bc8d28c3e62463565deabd2c32f2b64d18e549a) | 2026-09-22 | Nueva | Cambio | 9 | Persist conflict zone runtime state |
| [91a0045d5](https://github.com/AAEmu/AAEmu/commit/91a0045d5d678ee8a610b9e843133a2932dc6389) | 2026-09-22 | Nueva | Cambio | 3 | Retry scheduled conflict state persistence |
| [4e31d4fea](https://github.com/AAEmu/AAEmu/commit/4e31d4fea60995f5ed48ac779560fccb07cbed12) | 2026-09-22 | Nueva | Cambio | 10 | feat(world): wire monitor NPC lifecycle and boss telescope |
| [bfa214e11](https://github.com/AAEmu/AAEmu/commit/bfa214e110d897838d4ee2971184b8bd1d7ac657) | 2026-09-22 | Nueva | Merge | 5 | Merge pull request #1666 from NickMesser/codex/wave2-gf-w05 |
| [a5e70afec](https://github.com/AAEmu/AAEmu/commit/a5e70afece8d3c5e5de36fbdbef589ece418cec3) | 2026-09-22 | Nueva | Merge | 3 | Merge pull request #1668 from NickMesser/codex/wave2-gf-q06 |
| [809505d3b](https://github.com/AAEmu/AAEmu/commit/809505d3bde35d1fcc9f7dbedb80eaa5198d8360) | 2026-09-22 | Nueva | Merge | 4 | Merge pull request #1669 from NickMesser/codex/wave2-gf-q09 |
| [4b4eee2ab](https://github.com/AAEmu/AAEmu/commit/4b4eee2aba2e4a2a5dd1c2d3471034aaa278467a) | 2026-09-22 | Nueva | Merge | 6 | Merge pull request #1671 from NickMesser/codex/wave2-gf-q10 |
| [f602aac4e](https://github.com/AAEmu/AAEmu/commit/f602aac4eec67ec687ff52b69cc85ab95b3842d7) | 2026-09-22 | Nueva | Merge | 10 | Merge pull request #1674 from NickMesser/codex/wave2-gf-w11 |
| [3422e0e4e](https://github.com/AAEmu/AAEmu/commit/3422e0e4e562b03a5db9d18074f09f80090c1327) | 2026-09-22 | Nueva | Cambio | 2 | fix(skills): gate Reversal transfers on tag immunity |
| [3c2af118f](https://github.com/AAEmu/AAEmu/commit/3c2af118f45933b6c106e07698d8d02b2ab1c784) | 2026-09-22 | Nueva | Cambio | 3 | fix(craft-order): wipe the board atomically and drop a row that outlived a failed post |
| [99c8c6f4a](https://github.com/AAEmu/AAEmu/commit/99c8c6f4a727984acfb2b1b944713c370e4ebd47) | 2026-09-22 | Nueva | Cambio | 5 | fix(character): reject face-less beauty blocks and protect lobby buffs |
| [201832fea](https://github.com/AAEmu/AAEmu/commit/201832fea39111ffc2e951fadcc979158bab92ce) | 2026-09-22 | Nueva | Cambio | 7 | fix(factions): publish sweeps, seed zones with content, ignore late denials |
| [15756b6b2](https://github.com/AAEmu/AAEmu/commit/15756b6b2bba41c242c7cf19dcf858508e8464ae) | 2026-09-22 | Nueva | Merge | 9 | Merge pull request #1665 from NickMesser/codex/gunslinger-targets-reversal |
| [5ae16c9f9](https://github.com/AAEmu/AAEmu/commit/5ae16c9f925c64e212cae90082ed6f5be7347028) | 2026-09-22 | Nueva | Cambio | 7 | fix(quests): place the starter chain report bodies and audit starter actors |
| [982df3e7f](https://github.com/AAEmu/AAEmu/commit/982df3e7f6729256341298eac8adf61401d36884) | 2026-09-21 | Nueva | Cambio | 6 | fix(skills): send the client's bytes for the two requirement results it has no symbol for |
| [5fa3de149](https://github.com/AAEmu/AAEmu/commit/5fa3de149411b24463f68c88622496b92ad776ac) | 2026-09-21 | Nueva | Cambio | 1 | test(skills): pin the LeadershipPeriod pass on the content row shape |
| [e030d7680](https://github.com/AAEmu/AAEmu/commit/e030d76807f0f598714b8db62d3afc604baaeac5) | 2026-09-22 | Nueva | Cambio | 13 | fix(quests): grade-gate item group gathers and limit team effect fires |
| [550bdacf0](https://github.com/AAEmu/AAEmu/commit/550bdacf086af7234c3b39d6f87e0d7f649d0bd8) | 2026-09-22 | Nueva | Cambio | 5 | perf(siege): keep the offense raid team roster in memory |
| [33d964f30](https://github.com/AAEmu/AAEmu/commit/33d964f3054750dc39af9618275ada1095841e6b) | 2026-09-22 | Nueva | Cambio | 4 | fix(zones): ship the conflict state table in the dump and persist off the state lock |
| [244c7c370](https://github.com/AAEmu/AAEmu/commit/244c7c3705cabbc4073bf7a65896a07d4c23e318) | 2026-09-22 | Nueva | Merge | 6 | Merge pull request #1653 from NickMesser/fix/craft-order-followups |
| [46a3ed98a](https://github.com/AAEmu/AAEmu/commit/46a3ed98a87e650877f00a6598d4874810142c26) | 2026-09-21 | Nueva | Cambio | 28 | feat(indun): load every action, event and round kind and drive dungeon rounds |
| [bebd6c8d1](https://github.com/AAEmu/AAEmu/commit/bebd6c8d1a24de289f7d9f5edb82fa30d64a7a6b) | 2026-09-22 | Nueva | Cambio | 9 | fix(indun): gate a phase change on one timer read and report the round reached |
| [d81d661db](https://github.com/AAEmu/AAEmu/commit/d81d661dbc7e77d2d775881914d0ef95ef596973) | 2026-09-22 | Nueva | Merge | 29 | Merge pull request #1658 from NickMesser/feat/faction-diplomacy |
| [914cb8383](https://github.com/AAEmu/AAEmu/commit/914cb8383e92b66153369d01c41067ea64b912fc) | 2026-09-21 | Nueva | Cambio | 11 | feat(items): route item procs by chance kind and fix their target |
| [38af8196b](https://github.com/AAEmu/AAEmu/commit/38af8196bf85cb6fe7fb55e3efb437bfc3d150ca) | 2026-09-22 | Nueva | Cambio | 4 | fix(items): cast item procs past the gcd gate and read the wearer's health band |
| [3bb97971a](https://github.com/AAEmu/AAEmu/commit/3bb97971adc3e0fc5319f49b27013e10a3bc5678) | 2026-09-22 | Nueva | Merge | 6 | Merge pull request #1651 from NickMesser/fix/skill-result-mapping |
| [28814fbd4](https://github.com/AAEmu/AAEmu/commit/28814fbd45f064f3ded345afb83404efde4aafce) | 2026-09-22 | Nueva | Merge | 7 | Merge pull request #1661 from NickMesser/fix/starter-quest-actors |
| [c96aa8f99](https://github.com/AAEmu/AAEmu/commit/c96aa8f998575d95b89610e5fbfdea402688457b) | 2026-09-21 | Nueva | Cambio | 36 | feat(team): implement raid recruitment board and applicants |
| [873c99bb5](https://github.com/AAEmu/AAEmu/commit/873c99bb523d11965e4b1227a208bbaa6ba70446) | 2026-09-22 | Nueva | Cambio | 6 | fix(team): seat raid recruits within the post headcount and follow a solo poster into their team |
| [32981d4a0](https://github.com/AAEmu/AAEmu/commit/32981d4a0364bc942f6777f8ec915c88d51907b8) | 2026-09-22 | Nueva | Merge | 10 | Merge pull request #1672 from NickMesser/codex/wave2-gf-w06 |
| [57335d77e](https://github.com/AAEmu/AAEmu/commit/57335d77efbf59500322e141bd2cc79cf931cd13) | 2026-09-22 | Nueva | Cambio | 5 | Clean nation state during character deletion |
| [0ef51830f](https://github.com/AAEmu/AAEmu/commit/0ef51830f9525ed5a4f5b5c0aa9a300cda4e66e1) | 2026-09-22 | Nueva | Merge | 16 | Merge pull request #1655 from NickMesser/feat/skill-target-semantics |
| [0ad3cf2ce](https://github.com/AAEmu/AAEmu/commit/0ad3cf2ce9f7fc44d0defeade00a736b61050fbe) | 2026-09-22 | Nueva | Cambio | 1 | Update README with AAEmu 10.x setup link |
| [f853657b5](https://github.com/AAEmu/AAEmu/commit/f853657b5a23905ccc36a0180f04ce3b84c2405d) | 2026-09-22 | Nueva | Cambio | 2 | fix(character): accept the client's full scar transform range |
| [56ca983bf](https://github.com/AAEmu/AAEmu/commit/56ca983bf9ab92423ea821d1ed8b2d5200ffc112) | 2026-09-22 | Nueva | Cambio | 3 | fix(items): refuse an item proc while its skill is on cooldown |
| [f282bb807](https://github.com/AAEmu/AAEmu/commit/f282bb807e7baf764bca2daf802e787a254954eb) | 2026-09-22 | Nueva | Cambio | 5 | fix(quests): re-count gated item groups when a grade changes in place |
| [8e7cf5f14](https://github.com/AAEmu/AAEmu/commit/8e7cf5f14a0aeebc2898e5143e1f5f6c9c8e8800) | 2026-09-22 | Nueva | Cambio | 3 | fix(indun): keep the no-aggro wipe check clear of a killing blow |
| [0d048ae0b](https://github.com/AAEmu/AAEmu/commit/0d048ae0b896a054bd6f618a93e4a3c122935e79) | 2026-09-22 | Nueva | Cambio | 2 | fix(units): obsolete attribute 127 now that no content row uses it |
| [21ec808f2](https://github.com/AAEmu/AAEmu/commit/21ec808f2f6af44187fd4a2eabd3b9df976d4677) | 2026-09-22 | Nueva | Cambio | 0 | chore: trigger CI |
| [cbd6eed21](https://github.com/AAEmu/AAEmu/commit/cbd6eed215c98ca64d2d82be705b063708e87ae1) | 2026-09-22 | Nueva | Cambio | 11 | Implement instance exit and difficulty doodad functions |
| [51f1fcbbc](https://github.com/AAEmu/AAEmu/commit/51f1fcbbc8fbeaf87927d349c21befd7d1a6daf5) | 2026-09-22 | Nueva | Cambio | 2 | fix(doodads): let only the party owner open the instance difficulty picker |
| [900da53ad](https://github.com/AAEmu/AAEmu/commit/900da53ad2c196d031a6a07306b7d1b426701f2f) | 2026-09-22 | Nueva | Cambio | 38 | feat(quests): implement the remaining Start, Ready and Reward act types |
| [8259c4ca3](https://github.com/AAEmu/AAEmu/commit/8259c4ca34f65ea477b2dcb984c9339803e1e12a) | 2026-09-22 | Nueva | Cambio | 6 | fix(quests): complete resident point rewards and refuse Start level range accepts |
| [28dcfc05e](https://github.com/AAEmu/AAEmu/commit/28dcfc05e4e6b3f3803df4796f7a2f1c8f9d4a9e) | 2026-09-22 | Nueva | Cambio | 1 | fix(quests): check the Start level range before the context requirements |
| [9242f7cb1](https://github.com/AAEmu/AAEmu/commit/9242f7cb132ef0b5db7e7d59ab46a468161aabf7) | 2026-09-22 | Nueva | Merge | 47 | Merge pull request #1657 from NickMesser/feat/quest-progress-acts |
| [b87d2d225](https://github.com/AAEmu/AAEmu/commit/b87d2d22575f9198b816f49b4628a39e4f9d82ef) | 2026-09-22 | Nueva | Merge | 28 | Merge pull request #1654 from NickMesser/feat/indun-actions-events-rounds |
| [d6aadd485](https://github.com/AAEmu/AAEmu/commit/d6aadd48533384e0b601381cec709472a3fb9a4c) | 2026-09-22 | Nueva | Merge | 11 | Merge pull request #1675 from NickMesser/codex/wave2-gf-q08 |
| [165c59104](https://github.com/AAEmu/AAEmu/commit/165c5910490d397765f69c23a5fc907d3f8c7183) | 2026-09-22 | Nueva | Merge | 38 | Merge pull request #1664 from NickMesser/feat/quest-remaining-acts |
| [57b7cf093](https://github.com/AAEmu/AAEmu/commit/57b7cf0933cc723cf3cfa0216dc648c308bbf0c2) | 2026-09-22 | Nueva | Merge | 37 | Merge pull request #1660 from NickMesser/feat/raid-recruitment |
| [156f1ac6f](https://github.com/AAEmu/AAEmu/commit/156f1ac6f72fa4e0bd0a326c8325ddc4184f9658) | 2026-09-22 | Nueva | Merge | 5 | Merge pull request #1673 from NickMesser/codex/wave2-gf-s02 |
| [ac4e243a2](https://github.com/AAEmu/AAEmu/commit/ac4e243a29ef0f6ceb8f7a50141012e6f6a96282) | 2026-09-22 | Nueva | Merge | 17 | Merge pull request #1663 from NickMesser/feat/character-edit-beauty |
| [e586d1556](https://github.com/AAEmu/AAEmu/commit/e586d1556b9375c6a8bbd9c6ca9c78f7a168d56b) | 2026-09-22 | Nueva | Merge | 9 | Merge pull request #1667 from NickMesser/codex/wave2-gf-s04 |
| [acc133b5e](https://github.com/AAEmu/AAEmu/commit/acc133b5e670d7460806ff03420602895efe94ef) | 2026-09-22 | Nueva | Cambio | 12 | feat(chat): enforce faction and trial authorization |
| [328f2653c](https://github.com/AAEmu/AAEmu/commit/328f2653c2c8d7259f25bbc9b67a3b23cfb5abfc) | 2026-09-22 | Nueva | Cambio | 5 | fix(chat): keep faction and trial chat on the joined channel |
| [bb8de1413](https://github.com/AAEmu/AAEmu/commit/bb8de1413d50ffb2163cc4ac8d8aaea2577e0401) | 2026-09-22 | Nueva | Cambio | 1 | fix(chat): move a crime-driven pirate's faction channel |
| [ad0942d44](https://github.com/AAEmu/AAEmu/commit/ad0942d44f40714e1fd8ad9273644b882e0ca492) | 2026-09-22 | Nueva | Cambio | 6 | feat(indun): enforce admission schedules and buff tags |
| [ec2484b6c](https://github.com/AAEmu/AAEmu/commit/ec2484b6cdfe8b81465c86bdff92a10786affd11) | 2026-09-22 | Nueva | Cambio | 4 | fix(indun): recheck admission before prepared entry |
| [74d8ab710](https://github.com/AAEmu/AAEmu/commit/74d8ab710292ca724ea4a70db835b7b190d24146) | 2026-09-22 | Nueva | Cambio | 3 | fix(indun): keep dungeon rejoin reachable while the entrance window is closed |
| [4833c176d](https://github.com/AAEmu/AAEmu/commit/4833c176d2ac099d9e3c2ad44aa76c69b245dafa) | 2026-09-22 | Nueva | Cambio | 3 | fix(indun): refuse a closed entrance when applying to the queue |
| [c9c4f9455](https://github.com/AAEmu/AAEmu/commit/c9c4f9455ee58c41a48606f3e6d472f67d9ef864) | 2026-09-22 | Nueva | Cambio | 1 | fix(indun): answer false when a squad is refused at apply time |
| [468ac974b](https://github.com/AAEmu/AAEmu/commit/468ac974b22ec1b06a75eb23c7b267b682eedbf2) | 2026-09-22 | Nueva | Cambio | 1 | fix(skills): keep a pure-unsupported cast from rolling fire_skill procs |
| [76d25d1c4](https://github.com/AAEmu/AAEmu/commit/76d25d1c4998398ec0ecce32846fd6c3e991db88) | 2026-09-22 | Nueva | Merge | 11 | Merge pull request #1649 from NickMesser/feat/item-proc-events |
| [3ff6ec31a](https://github.com/AAEmu/AAEmu/commit/3ff6ec31ae7244650d094f4376276975de6ebbc0) | 2026-09-22 | Nueva | Merge | 8 | Merge pull request #1670 from NickMesser/codex/wave2-gf-w02 |
| [f89c7ea8e](https://github.com/AAEmu/AAEmu/commit/f89c7ea8e8cce9f39b4be9f490d0e904fe402ba6) | 2026-09-22 | Nueva | Merge | 13 | Merge pull request #1676 from NickMesser/codex/wave2-gf-s07 |
| [1304bc0f8](https://github.com/AAEmu/AAEmu/commit/1304bc0f8a4c8a2617c7c4bef52d888b8f8af782) | 2026-09-22 | Nueva | Cambio | 2 | Fix null customization body part rows |
| [93ed326a1](https://github.com/AAEmu/AAEmu/commit/93ed326a1d0bdfc170f34b9e488fb6912286a22d) | 2026-09-22 | Nueva | Merge | 2 | Merge pull request #1677 from NickMesser/codex/fix-null-customization-body-part |
| [e7439734e](https://github.com/AAEmu/AAEmu/commit/e7439734ee046cb208a6c377c9b03a8a13c05450) | 2026-09-22 | Nueva | Cambio | 14 | feat(ucc): add UCC apply integrity and house UCC slot persistence |
| [79bdb5843](https://github.com/AAEmu/AAEmu/commit/79bdb5843ba7309366f9fd0f199a4f0da2913328) | 2026-09-22 | Nueva | Cambio | 15 | feat(mail): cover spam-report, cod payment and return/expiry mail protocols |
| [bc498f03e](https://github.com/AAEmu/AAEmu/commit/bc498f03e67d8dbaf845d762f9969d2cbcd071c3) | 2026-09-22 | Nueva | Cambio | 12 | feat(weather): implement schedule-driven rain and wind weather phases |
| [82f3ead23](https://github.com/AAEmu/AAEmu/commit/82f3ead23c61b03cbdda11f1249167585740a6d8) | 2026-09-22 | Nueva | Cambio | 10 | fix(weather): keep snow the cycle did not turn on and drop rain and wind |
| [c28e63529](https://github.com/AAEmu/AAEmu/commit/c28e635292e9a9c3c6f6049066c9ad24e0a996cf) | 2026-09-22 | Nueva | Cambio | 9 | fix(mail): send the client's charge-paid letter and return unpaid or reported COD mail |
| [76794e92c](https://github.com/AAEmu/AAEmu/commit/76794e92cbbeb7582bddc53af3ec3f5a53d34177) | 2026-09-23 | Nueva | Cambio | 14 | fix(ucc): spend the named crest stamp, gate targets on ucc_applicables and clean up removed houses |
| [e5baa70f3](https://github.com/AAEmu/AAEmu/commit/e5baa70f39b7ec6e5375d598fd46ba9eb8cc7ac6) | 2026-09-22 | Nueva | Merge | 16 | Merge pull request #1682 from Razymex/feat/weather-rain-wind |
| [83e9e4480](https://github.com/AAEmu/AAEmu/commit/83e9e4480264a797e0edbffe71be71b2beeb6f82) | 2026-09-22 | Nueva | Merge | 13 | Merge pull request #1681 from Razymex/feat/mail-edge-protocols |
| [2da574078](https://github.com/AAEmu/AAEmu/commit/2da57407816ef7830f3d883b8aa4e2ead92e30c4) | 2026-09-22 | Nueva | Merge | 16 | Merge pull request #1680 from Razymex/feat/ucc-integrity-apply |
| [14036d29f](https://github.com/AAEmu/AAEmu/commit/14036d29f85335aca8645f88c1b431e8e9605691) | 2026-09-22 | Nueva | Cambio | 11 | feat(collections): add collection and encyclopedia discovery rewards |
| [b91923860](https://github.com/AAEmu/AAEmu/commit/b919238605b0cf37587aaf8aca866a6900e42a7f) | 2026-09-22 | Nueva | Cambio | 2 | feat(housing): complete house sale listing, settlement and persistence paths |
| [fd8309736](https://github.com/AAEmu/AAEmu/commit/fd83097360f0c2e06d777f311f10cb61af551d84) | 2026-09-22 | Nueva | Cambio | 7 | fix(collections): defer discovery until progress loads and honour watched item grades |
| [da4ecc11e](https://github.com/AAEmu/AAEmu/commit/da4ecc11ec742dc3e36115981f49a8c950d9188b) | 2026-09-23 | Nueva | Cambio | 4 | fix(housing): commit a house sale after releasing its lock |
| [0ac9f1180](https://github.com/AAEmu/AAEmu/commit/0ac9f11805f1eb1f8c9420648af782755cb43131) | 2026-09-23 | Nueva | Cambio | 5 | fix(collections): report a grade reached on an item already held |
| [34db4fba1](https://github.com/AAEmu/AAEmu/commit/34db4fba1b3d315fafaf2e11066557ab80ada7a2) | 2026-09-23 | Nueva | Cambio | 4 | fix(housing): refuse a house-sale cancel that has no character |
| [94fe6dc13](https://github.com/AAEmu/AAEmu/commit/94fe6dc13f09d0e559017f94b379446f66c90746) | 2026-09-22 | Nueva | Merge | 4 | Merge pull request #1678 from Razymex/feat/housing-trade-sale |
| [e20cb8269](https://github.com/AAEmu/AAEmu/commit/e20cb8269cf4a76647c6bae0005c0eec2c75a31b) | 2026-09-22 | Nueva | Merge | 15 | Merge pull request #1679 from Razymex/feat/collections-encyclopedia |
| [6bb2e53f5](https://github.com/AAEmu/AAEmu/commit/6bb2e53f5e17170c7be44938ee38b97fc0132d9c) | 2026-09-23 | Nueva | Cambio | 2 | fix(housing): load the for-sale sign doodad from const_doodad_types |
| [043c10c58](https://github.com/AAEmu/AAEmu/commit/043c10c58fb8cbaf50e4d8fa3862c7ea707daa31) | 2026-09-23 | Nueva | Merge | 2 | Merge pull request #1688 from Razymex/bugfix/housing-trade-followups |
| [212b864a5](https://github.com/AAEmu/AAEmu/commit/212b864a51db28360f522215dfd0be2c7b3df725) | 2026-09-23 | Nueva | Cambio | 13 | feat(music): instrument doodad ownership and play application |
| [a7ad802d2](https://github.com/AAEmu/AAEmu/commit/a7ad802d253f88720c8476761cce208f6a1b79f5) | 2026-09-23 | Nueva | Cambio | 21 | feat(instances): authorize zone permission and difficulty changes |
| [09fd4fe48](https://github.com/AAEmu/AAEmu/commit/09fd4fe4825a2355b133cde7b7f7d540053d26d4) | 2026-09-23 | Nueva | Cambio | 6 | fix(music): play slave instruments and resend a resumed score |
| [1951b19fa](https://github.com/AAEmu/AAEmu/commit/1951b19fa8e9d3d9474aa641c79a65917a79d1b9) | 2026-09-23 | Nueva | Cambio | 6 | fix(indun): stop sending an empty zone-permission refresh |
| [c9f9c8d8a](https://github.com/AAEmu/AAEmu/commit/c9f9c8d8ab349af780cdd121d486b79ff3bbb7dc) | 2026-09-23 | Nueva | Merge | 20 | Merge pull request #1684 from Razymex/feat/zone-permission-instance-controls |
| [b64bf5be2](https://github.com/AAEmu/AAEmu/commit/b64bf5be297939614c469dd0ad599534401d2a74) | 2026-09-23 | Nueva | Merge | 13 | Merge pull request #1690 from Razymex/feat/solo-music-instruments |
| [b20ddfa4a](https://github.com/AAEmu/AAEmu/commit/b20ddfa4a251c4749d703d6d30a06054ec2e4dda) | 2026-09-23 | Nueva | Cambio | 9 | feat(housing): house UCC apply broadcast and rotated plot geometry |
| [1720c48f3](https://github.com/AAEmu/AAEmu/commit/1720c48f3547f829ea2daacaedfa17c21dc96285) | 2026-09-23 | Nueva | Cambio | 2 | fix(housing): drop the unused UCC apply material config |
| [43efbb4a4](https://github.com/AAEmu/AAEmu/commit/43efbb4a484b00dfe372c4c1a63ad6517e539115) | 2026-09-23 | Nueva | Cambio | 24 | feat(quests): add saga-group progression with grant-once rewards |
| [e8740a5bc](https://github.com/AAEmu/AAEmu/commit/e8740a5bc77071662851e70f3e0da9ff015bcad1) | 2026-09-23 | Nueva | Cambio | 1 | fix(quests): accept milestone-scoped grants in the saga reward ledger |
| [689754ade](https://github.com/AAEmu/AAEmu/commit/689754adebcc99a1ab12788b42abcd8fd3696cbc) | 2026-09-23 | Nueva | Cambio | 1 | Revert "fix(quests): accept milestone-scoped grants in the saga reward ledger" |
| [7424d7960](https://github.com/AAEmu/AAEmu/commit/7424d79601309a767173e126a7e628def6af742c) | 2026-09-23 | Nueva | Merge | 24 | Merge pull request #1683 from Razymex/feat/saga-group-progression |
| [c4da6d31f](https://github.com/AAEmu/AAEmu/commit/c4da6d31f2435e84be91b4ad8d3369f42511e81c) | 2026-09-23 | Nueva | Merge | 7 | Merge pull request #1687 from Razymex/feat/housing-ucc-plot-geometry |
| [9cf51412c](https://github.com/AAEmu/AAEmu/commit/9cf51412c2facdd50f4e02023cda4b2574c96a5a) | 2026-09-23 | Nueva | Cambio | 22 | feat(residents): local development progression and resident settlement |
| [b170b2ccc](https://github.com/AAEmu/AAEmu/commit/b170b2ccc6eb2aaa462b4a97deda1d67ba79ddaa) | 2026-09-23 | Nueva | Cambio | 10 | fix(residents): gate the dev packets and stop pushing tribute phases |
| [dda96e5cb](https://github.com/AAEmu/AAEmu/commit/dda96e5cb9646d4b875f6ae875d79de21b3daee6) | 2026-09-23 | Nueva | Cambio | 13 | fix(residents): drop unused local-development state |
| [e500b1d76](https://github.com/AAEmu/AAEmu/commit/e500b1d76bd1731a7b1c89d6c0559f2273da46f4) | 2026-09-23 | Nueva | Merge | 21 | Merge pull request #1692 from Razymex/feat/local-development-resident |
| [ee2c8f7c4](https://github.com/AAEmu/AAEmu/commit/ee2c8f7c447467a59459dcb30e07b6c775b925fc) | 2026-09-23 | Nueva | Cambio | 3 | fix(skills): learn the base skill when an ancestral successor is chosen |
| [543ad3a0d](https://github.com/AAEmu/AAEmu/commit/543ad3a0d9bb2cb6233468c47094cf135b609a6e) | 2026-09-23 | Nueva | Cambio | 1 | fix(skills): scope the ancestral activation tests to their own skill manager |
| [5fc4f6c7d](https://github.com/AAEmu/AAEmu/commit/5fc4f6c7ddb72b9e93e8f46bcef42845aca02429) | 2026-09-23 | Nueva | Cambio | 28 | feat(merchants): random merchant windows with exactly-once purchases |
| [12ac37614](https://github.com/AAEmu/AAEmu/commit/12ac376144bb77ba9c1423e88385f1b246b6c163) | 2026-09-23 | Nueva | Cambio | 10 | fix(merchants): read the shop window and claim the offer that was shown |
| [9d012b4ea](https://github.com/AAEmu/AAEmu/commit/9d012b4eab71381b7844637688c4bfd72fe88c20) | 2026-09-23 | Nueva | Cambio | 1 | fix(merchants): store shop roll times as whole seconds |
| [f2282e590](https://github.com/AAEmu/AAEmu/commit/f2282e590165b31ed3935f34a2f04e0936a438ed) | 2026-09-23 | Nueva | Merge | 30 | Merge pull request #1693 from Razymex/feat/random-merchants |
| [b73c33aa7](https://github.com/AAEmu/AAEmu/commit/b73c33aa761dac418472fa85c7e0985dc98abb73) | 2026-09-23 | Nueva | Merge | 3 | Merge pull request #1698 from Razymex/bugfix/heir-skill-activate |
