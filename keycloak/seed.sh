#!/usr/bin/env bash
# Seeds each user's "last login" state, computed fresh relative to *now* on every
# run. That keeps the boundary cases around the 120-day threshold correct no
# matter what day you run this on (nothing here is a hard-coded calendar date).
#
# It seeds two things, so either cleanup approach works out of the box:
#   1. a `lastLogin` user attribute   - the simplification this exercise centres on
#   2. a real, backdated Keycloak LOGIN event per user, in the events store
#
# Idempotent: re-running overwrites the attribute and re-inserts the events.
# `make up` runs this for you; re-run any time with `make seed`.

set -euo pipefail

KC="${KC_CONTAINER:-iam-takehome-keycloak}"
PG="${PG_CONTAINER:-iam-takehome-postgres}"
REALM="${REALM:-acme}"
LOGIN_CLIENT="${LOGIN_CLIENT:-acme-portal}"

# username | user id (must match keycloak/realm-export.json) | days since last login | note
USERS=(
  "alice|9b7667a2-1e74-4d34-95af-988132b1875b|210|old - should be cleaned"
  "bob|a06ca1a9-daf8-4219-b8c0-311868309a29|175|old - should be cleaned"
  "carol|52bc2c45-c1cc-4c88-b354-af9fdae4c631|150|old - should be cleaned"
  "dave|8937fea5-08c7-45d9-82cb-86e36c426542|124|just over threshold - should be cleaned at default 120"
  "eve|6c175a9c-52ba-469b-b560-ca896225b20d|116|just under threshold - should NOT be cleaned at default 120"
  "frank|8b45823d-a818-478d-9c70-592d168c249a|60|recent - safe"
  "grace|61a7a5b6-8259-4e6a-a887-61c0f0fe6b03|21|recent - safe"
  "heidi|21b075dd-87f2-45fd-99a7-4e5b6d22d87c|3|very recent - safe"
  "break-glass|6700192e-6778-4390-9c5c-dfc3f0398041|320|admin-flavored - should be EXCLUDED even though very old"
)

NOW_MS=$(( $(date +%s) * 1000 ))
DAY_MS=$(( 86400 * 1000 ))

echo "Configuring kcadm credentials..."
docker exec "$KC" /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin >/dev/null

# event_entity.realm_id stores the realm's internal id, not its name. Look it up.
REALM_ID=$(docker exec "$PG" psql -U keycloak -d keycloak -tA \
  -c "SELECT id FROM realm WHERE name='${REALM}';" | tr -d '[:space:]')

# Idempotency: clear previously-seeded LOGIN events before re-inserting.
docker exec "$PG" psql -U keycloak -d keycloak -q \
  -c "DELETE FROM event_entity WHERE realm_id='${REALM_ID}' AND type='LOGIN';" >/dev/null

echo "Seeding lastLogin attributes + backdated LOGIN events (relative to now)..."
for row in "${USERS[@]}"; do
  IFS='|' read -r user uid days note <<< "$row"
  ts=$(( NOW_MS - days * DAY_MS ))

  # 1. lastLogin attribute (an unmanaged attribute; the realm allows these -
  #    see the userProfile component in realm-export.json).
  docker exec "$KC" /opt/keycloak/bin/kcadm.sh update "users/${uid}" -r "$REALM" \
    -s "attributes={\"lastLogin\":[\"${ts}\"],\"note\":[\"${note}\"]}" >/dev/null

  # 2. a real, backdated LOGIN event in the events store.
  evid=$(uuidgen | tr 'A-Z' 'a-z')
  docker exec "$PG" psql -U keycloak -d keycloak -q -v ON_ERROR_STOP=1 \
    -c "INSERT INTO event_entity
          (id, client_id, details_json, ip_address, realm_id, session_id, event_time, type, user_id)
        VALUES
          ('${evid}', '${LOGIN_CLIENT}', '{\"auth_method\":\"openid-connect\",\"username\":\"${user}\"}',
           '203.0.113.10', '${REALM_ID}', '${evid}', ${ts}, 'LOGIN', '${uid}');" >/dev/null

  printf "  %-12s last login %4s days ago\n" "$user" "$days"
done

echo ""
echo "Done. Both approaches are usable now:"
echo "  attribute : GET /admin/realms/${REALM}/users        -> attributes.lastLogin (epoch ms)"
echo "  events    : GET /admin/realms/${REALM}/events?type=LOGIN&user={id}"
