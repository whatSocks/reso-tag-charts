from django.contrib import admin as dj_admin
from django_neomodel import admin as neo_admin
from neomodel import db as db

from .models import TrackGroup, Tag, Track, RUser

class RUserAdmin(dj_admin.ModelAdmin):
    list_display = ('uuid','uuid')
neo_admin.register(RUser, RUserAdmin)

class TrackGroupAdmin(dj_admin.ModelAdmin):
    list_display = ('title','type','uuid')
    ordering = ['title']
    actions = ['import_playlists','import_trackgroups']


    def import_tracks(self):
        tracks_query = '''
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
            '''
        db.cypher_query(tracks_query)

    # this is a hack - use only for initial import
    def import_playlists(self, response, queryset):
        playlists_query = '''
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
            '''
        db.cypher_query(playlists_query)
        self.import_tracks()

    import_playlists.short_description = 'Import Playlists (ignores queryset)'

    # this is a hack - use only for initial import
    def import_trackgroups(self, response, queryset):
        trackgroups_query = '''
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
            '''
        db.cypher_query(trackgroups_query)
        self.import_tracks()

    import_trackgroups.short_description = 'Import Pg 1 (ignores queryset)'

neo_admin.register(TrackGroup, TrackGroupAdmin)

class TagAdmin(dj_admin.ModelAdmin):
    list_display = ('name','tg_count','uuid')
    ordering = ['name']
    actions = ['import_tags','set_tg_count']

    # this is a hack, do it in code not cypher to better handle errors
    def import_tags(self, response, queryset):
        query = '''
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
            '''
        db.cypher_query(query)

    import_tags.short_description = 'Import Tags (ignores queryset)'

    # this is a hack 
    def set_tg_count(self, response, queryset):
        query = '''
			MATCH (tag:Tag)<-[:HAS_TAG]-(tg:TrackGroup)
			WITH tag as tag, count(distinct tg) as tg_count
			SET tag.tg_count=tg_count

			// set tag relationships
			WITH tag
			MATCH (tag)-[r:RELATED]-()
			DELETE r

			WITH tag
			MATCH (tag)<-[:HAS_TAG]-(tg:TrackGroup)-[:HAS_TAG]->(m:Tag)<-[:HAS_TAG]-(tg2:TrackGroup)
			WHERE tg <> tg2
			AND tag.tg_count >= m.tg_count 
			MERGE (m)-[:RELATED]->(tag)
            '''
        db.cypher_query(query)

    set_tg_count.short_description = 'Set tg_count (ignores queryset)'


neo_admin.register(Tag, TagAdmin)

class TrackAdmin(dj_admin.ModelAdmin):
    list_display = ('title','uuid')
    ordering = ['title']
neo_admin.register(Track, TrackAdmin)