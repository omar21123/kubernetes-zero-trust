# Réseau, DNS et observabilité

## Matrice des nouvelles connexions

| Source | Destination | Port | Décision |
|---|---|---|---|
| frontend | api dans `zt-app` | TCP 8080 | Autorisé |
| api | catalog dans `zt-data` | TCP 8080 | Autorisé |
| Tous les pods des quatre namespaces | Pods CoreDNS de `kube-system` | UDP et TCP 53 | Autorisé |
| auditor, identifié par son ServiceAccount | Entité Cilium `kube-apiserver` | TCP 443 / 6443 | Autorisé au réseau ; requêtes ensuite soumises à RBAC |
| frontend | catalog directement | Tous | Refusé |
| probe | frontend, api, catalog | Tous | Refusé |
| catalog | api | Tous | Refusé |
| frontend, api, catalog, probe | API Kubernetes | Tous | Refusé |
| auditor | Services applicatifs | Tous | Refusé |
| Workloads | Internet ou autres destinations | Tous hors exceptions précédentes | Refusé |

Le trafic retour n'exige pas une règle inverse. Le catalogue n'a donc besoin d'aucune sortie vers l'API pour répondre à ses appels. Les connexions loopback à l'intérieur d'un même pod ne sont pas isolées par les NetworkPolicies.

## Mécanisme

`default-deny.yaml` sélectionne tous les pods dans chacun des quatre namespaces et active l'isolation ingress **et** egress. Pour une communication entre deux pods isolés, la sortie de la source et l'entrée de la destination doivent toutes deux être autorisées.

Les autorisations sont additives : une autre politique large peut rouvrir un flux. Une politique nommée Default Deny n'est pas une règle prioritaire qui annule tous les autres allows. Les sélecteurs namespace et pod d'un même élément sont combinés avec un **ET** ; les mettre dans deux éléments distincts produirait un **OU** et élargirait l'accès.

Les règles n'autorisent pas les flux node/host et les sondes kubelet de la même façon que les flux entre pods. Kubernetes prévoit des exceptions et limites pour le trafic du nœud hébergeant un pod ; le laboratoire ne promet pas d'isoler un nœud compromis.

## DNS

Les règles ciblent `kube-system` **et** `k8s-app: kube-dns`, sur UDP et TCP 53. Elles sont adaptées à CoreDNS tel que déployé par EKS (et par k3s dans la CI), avec le label `k8s-app: kube-dns`, pas à NodeLocal DNSCache ni à un résolveur externe. Le mode `dns` teste la résolution via le résolveur du pod ; `dns-tcp` effectue une vraie requête DNS sur TCP et vérifie une réponse A.

Résoudre le nom d'un service ne donne aucun droit de s'y connecter. Les tests de refus passent à la fois par le Service et par la PodIP, avec les flux autorisés comme contrôles positifs.

L'autorisation CoreDNS porte sur le transport, pas sur les noms interrogés. Un pod compromis pourrait tenter d'exfiltrer via des requêtes DNS relayées par CoreDNS. Un contrôle DNS L7 ou un filtrage sur le résolveur peut répondre à ce risque si les besoins métier le justifient.

## Extension Cilium HTTP L7

`python tools/lab.py l7-on` applique une règle de sortie pour le ServiceAccount frontend puis supprime `frontend-to-api`, l'allow L4 du même côté. Cela évite qu'une permission L4 additive ne rende le contrôle L7 inopérant. L'entrée L4 sur l'API reste nécessaire et ne dispense pas du contrôle de sortie.

L'extension autorise uniquement GET `/health` et GET `/catalog` vers l'API. GET `/admin`, pourtant accessible dans le profil de base, doit recevoir HTTP 403 du proxy Cilium. Le contrôle porte sur HTTP en clair. Un flux HTTPS de bout en bout exigerait une autre stratégie d'inspection ou une autorisation au niveau de l'application.

`l7-off` ou `deploy` restaure les autorisations L4 documentées. Ne pas appliquer le dossier `policies/optional` en même temps que toutes les politiques de base en espérant obtenir une restriction automatique.

## Observer avec Hubble

Le chart Cilium active Hubble, Relay et son interface. Ouvrir un tunnel local :

```console
kubectl -n kube-system port-forward service/hubble-ui 12000:80
```

Ouvrir [Hubble UI](http://localhost:12000), sélectionner le namespace et relancer les tests dans un autre terminal. Repérer frontend → api en `FORWARDED`, puis frontend → catalog et probe → api en `DROPPED` / `POLICY_DENIED` selon l'affichage de la version utilisée.

Pour une capture CLI, installer Hubble CLI puis, dans deux terminaux :

```console
kubectl -n kube-system port-forward service/hubble-relay 4245:80
```

```console
hubble observe --server localhost:4245 --from-namespace zt-edge --verdict DROPPED --follow
```

Un HTTP 403 RBAC est produit dans TLS par l'API server : Hubble ne le décode pas. Pour ce scénario, la preuve est la réponse reçue par `audit.py`. Hubble est un outil d'observation, pas un mécanisme supplémentaire d'autorisation.
