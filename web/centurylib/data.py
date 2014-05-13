import datetime
import time

from fastkml import kml, Document
from fastkml.geometry import Point

from centurylib import triangles
from centurylib.groundoverlay import GroundOverlay


def stations(dt, db, icon_href, prettyprint=False):
    """The stations active at one time.

    Takes a datetime and pymongo database. Returns list of KML Placemarks.
    """
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.microsecond == 0
    assert dt.tzinfo is None

    next_hour = dt + datetime.timedelta(hours=1)

    k = kml.KML(ns='')
    kdoc = Document(name='stations')

    # Positions of stations active in this hour. Needs index on 'ts'.
    pipeline = [{
        '$match': {
            'ts': {'$gte': dt, '$lt': next_hour},
            # Valid samples.
            'airTemperature.quality': '1'
        }
    }, {
        '$group': {
            '_id': '$st',
            'position': {'$first': '$position'},
            # Could average the temperatures, probably not worthwhile.
            'airTemperature': {'$first': '$airTemperature'},
        }
    }]

    start = time.time()
    cursor = db.data.aggregate(pipeline=pipeline, cursor={})
    n = 0
    for doc in cursor:
        station_mark = kml.Placemark(ns='', id=doc['_id'], name=doc['_id'])
        n += 1
        # GeoJSON and KML agree on the order: (longitude, latitude).
        try:
            station_mark.geometry = Point(*doc['position']['coordinates'])
        except (TypeError, KeyError):
            # Incomplete.
            pass

        kdoc.append(station_mark)

    # TODO: horribly inefficient.
    kml_triangles = triangles.triangles(dt, db)
    for t in kml_triangles:
        kdoc.append(t)

    overlay = GroundOverlay(ns='')
    overlay.geometry = [90, -90, 180, -180, 0]
    overlay.icon_href = icon_href
    kdoc.append(overlay)  # Fails with upstream fastkml, need to update it.

    print 'stations(%s):' % dt, time.time() - start, 'seconds', n, 'docs'
    k.append(kdoc)
    return k.to_string(prettyprint=prettyprint)