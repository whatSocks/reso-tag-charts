# Resonate Tag Charts

Search [Resonate](https://resonate.is/) ([code](https://github.com/resonatecoop/)) tags for top tracks. 

![Search Tags for Top Tracks](https://raw.githubusercontent.com/whatSocks/reso-tag-charts/main/img/search.png)

## Todos

- [ ] Add deployment instructions
- [x] Add "import data" functionality to admin
- [ ] Unit tests

## How to setup locally

### Install dependencies

```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Create your Neo4j database

You can manage your own database, or go to [Neo4j Aura](https://neo4j.com/cloud/aura/) for a fully managed database.

### Do the initial data import

Before you start, install the APOC plugin.  

#### Create Constraints

```
CREATE CONSTRAINT ON (a:Ruser) ASSERT a.uuid IS UNIQUE;
CREATE CONSTRAINT ON (a:TrackGroup) ASSERT a.uuid IS UNIQUE;
CREATE CONSTRAINT ON (a:Track) ASSERT a.uuid IS UNIQUE;
```

#### Add the first page of Playlists (a type of TrackGroup)

```
WITH 'https://api.resonate.coop/v2/' AS uri
CALL apoc.load.json(uri + 'trackgroups?type=playlist') // in this example, grabbing listener-generated playlists
YIELD value
UNWIND value["data"] as data
MERGE (u:RUser {uuid:toString(data["user"]["id"])})
MERGE (t:TrackGroup {uuid:toString(data["id"])})
MERGE (u)-[:OWNS]->(t)
SET t.title = data["title"]
SET t.type = data["type"]
SET t.slug = data["slug"]
SET t.tracks_imported = false
```

#### Add more TrackGroups

```
WITH 'https://api.resonate.coop/v2/' AS uri
CALL apoc.load.json(uri + 'trackgroups') // in this example, grabbing listener-generated playlists
YIELD value
UNWIND value["data"] as data
MERGE (u:RUser {uuid:toString(data["user"]["id"])})
MERGE (t:TrackGroup {uuid:toString(data["id"])})
MERGE (u)-[:OWNS]->(t)
SET t.title = data["title"]
SET t.type = data["type"]
SET t.slug = data["slug"]
SET t.tracks_imported = false
```

#### Add the tracks

```
CALL apoc.periodic.commit(
"MATCH (tg:TrackGroup)
WHERE NOT tg.tracks_imported 
SET tg.tracks_imported = true
WITH tg limit $limit
WITH 'https://api.resonate.coop/v2/' AS uri, tg.uuid as tg_id
CALL apoc.load.json(uri + 'trackgroups/' + tg_id )
yield value
UNWIND value['data']['items'] as items
MERGE (u:RUser {uuid:toString(items['track']['creator_id'])})
MERGE (track:Track {uuid:toString(items['track']['id'])})
MERGE (t)-[:HAS_TRACK]->(track)
MERGE (track)<-[:CREATED]-(u)
SET track.title = items['track']['title']
SET track.tags_imported = false
RETURN count(*)
",
{limit:10});
```

#### The Tags

```
CALL apoc.periodic.commit(
"
MATCH (u:RUser)-[:CREATED]->(track:Track)
WHERE not u.uuid  in ['7212','4315','4414'] // bad data
AND NOT track.tags_imported
SET track.tags_imported = true
WITH u as artist, u.uuid as user_id, count(DISTINCT track) as tracks,'https://api.resonate.coop/v2/' as uri
ORDER BY tracks desc
LIMIT $limit
CALL apoc.load.json(uri + 'artists/' + user_id + '/releases') // grabbing all
YIELD value
UNWIND value['data'] as data
UNWIND data['tags'] as tags
MERGE (t:TrackGroup {uuid:toString(data['id'])})
MERGE (user:RUser {uuid:toString(user_id)})-[:OWNS]->(t)
MERGE (tag:Tag {name:toLower(tags)})
MERGE (tag)<-[:HAS_TAG]-(t)
SET tag.uuid=apoc.create.uuid()
SET t.title = data['title']
SET t.type = data['type']
RETURN count(*)
",
{limit:10});
```

### Add export the NEO4J_BOLT_URL

```shell
export NEO4J_BOLT_URL=bolt://neo4j:password@host-or-ip:port
```

(this also works with Aura)

```shell
export NEO4J_BOLT_URL=neo4j+s://neo4j:password@host-or-ip:port
```

Run migrations and create your superuser (for the admin, this is using an SQLite database)

```
./manage.py migrate
./manage.py createsuperuser
```

### Run the server

```shell
python manage.py runserver
```

Now you should be able to access http://localhost:8000 and play with the app.


## How to deploy to Heroku

Go to your Heroku dashboard and create a new app and add its git remote to your local clone of this app.

Go your Heroku's app's settings and add the `NEO4J_BOLT_URL` environment variable with the correct credentials:

```NEO4J_BOLT_URL="bolt://neo4j:password@host-or-ip:port"```

Now you can push to Heroku:

```shell
git push heroku master
```

And thats all you need :)
