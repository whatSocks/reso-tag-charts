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

    # this is a hack - use only for initial import
    def import_playlists(self, response, queryset):
        query = '''
            WITH 'https://beta.stream.resonate.coop/api/v2/' AS uri
            CALL apoc.load.json(uri + 'trackgroups?type=playlist') // in this example, grabbing listener-generated playlists
            YIELD value
            UNWIND value["data"] as data
            MERGE (u:RUser {uuid:toString(data["user"]["id"])})
            MERGE (t:TrackGroup {uuid:toString(data["id"])})
            MERGE (u)-[:OWNS]->(t)
            SET t.title = data["title"]
            SET t.type = data["type"]
            SET t.slug = data["slug"]

            //part 2 - tracks
            with uri as uri, toString(data["id"]) as tg_id,t
            CALL apoc.load.json(uri + 'trackgroups/' + tg_id )
            yield value
            UNWIND value["data"]["items"] as items
            MERGE (u:RUser {uuid:toString(items["track"]["creator_id"])})
            MERGE (track:Track {uuid:toString(items["track"]["id"])})
            MERGE (t)-[:HAS_TRACK]->(track)
            MERGE (track)<-[:CREATED]-(u)
            SET track.title = items["track"]["title"]
            '''
        db.cypher_query(query)

    import_playlists.short_description = 'Import Playlists (ignores queryset)'

    # this is a hack - use only for initial import
    def import_trackgroups(self, response, queryset):
        query = '''
            WITH 'https://beta.stream.resonate.coop/api/v2/' AS uri
            CALL apoc.load.json(uri + 'trackgroups') // grabbing page 1 of everything else
            YIELD value
            UNWIND value["data"] as data
            MERGE (u:RUser {uuid:toString(data["user"]["id"])})
            MERGE (t:TrackGroup {uuid:toString(data["id"])})
            MERGE (u)-[:OWNS]->(t)
            SET t.title = data["title"]
            SET t.type = data["type"]
            SET t.slug = data["slug"]

            //part 2 - tracks
            with uri as uri, toString(data["id"]) as tg_id,t
            CALL apoc.load.json(uri + 'trackgroups/' + tg_id )
            yield value
            UNWIND value["data"]["items"] as items
            MERGE (u:RUser {uuid:toString(items["track"]["creator_id"])})
            MERGE (track:Track {uuid:toString(items["track"]["id"])})
            MERGE (t)-[:HAS_TRACK]->(track)
            MERGE (track)<-[:CREATED]-(u)
            SET track.title = items["track"]["title"]
            '''
        db.cypher_query(query)

    import_trackgroups.short_description = 'Import Pg 1 (ignores queryset)'

neo_admin.register(TrackGroup, TrackGroupAdmin)

class TagAdmin(dj_admin.ModelAdmin):
    list_display = ('name','uuid')
    ordering = ['name']
    actions = ['import_tags']

    # this is a hack 
    def import_tags(self, response, queryset):
        query = '''
			MATCH (u:RUser)-[:CREATED]->(t:Track)
			WITH u.uuid as user_id, count(DISTINCT t) as tracks,"https://beta.stream.resonate.coop/api/v2/" as uri
			ORDER BY tracks desc
			LIMIT 25
			CALL apoc.load.json(uri + 'artists/' + user_id + '/releases') // grabbing all
			YIELD value
			UNWIND value["data"] as data
			UNWIND data["tags"] as tags
			MERGE (t:TrackGroup {uuid:toString(data["id"])})
			MERGE (user)-[:OWNS]->(t)
			MERGE (tag:Tag {name:toLower(tags)})
			MERGE (tag)<-[:HAS_TAG]-(t)
			SET tag.uuid=apoc.create.uuid()
			SET t.title = data["title"]
			SET t.type = data["type"]
            '''
        db.cypher_query(query)

    import_tags.short_description = 'Import Tags (ignores queryset)'

neo_admin.register(Tag, TagAdmin)

class TrackAdmin(dj_admin.ModelAdmin):
    list_display = ('title','uuid')
    ordering = ['title']
neo_admin.register(Track, TrackAdmin)