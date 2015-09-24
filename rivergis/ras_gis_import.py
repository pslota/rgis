# -*- coding: utf-8 -*-

__author__ = 'Łukasz Dębek'

from qgis.core import QGis

class HecRasExport(object):
    """
    Exporting model to RAS GIS Import file.
    """
    def __init__(self, rgis):
        self.rgis = rgis
        self.dbname = rgis.rdb.dbname
        self.host = rgis.rdb.host
        self.schema = rgis.rdb.SCHEMA
        self.srid = rgis.rdb.SRID
        self.nor = self.number_of_reaches()
        self.nox = self.number_of_xsections()
        self.se = self.spatial_extent()
        self.su = self.spatial_unit()

    def number_of_reaches(self):
        qry = 'SELECT COUNT("ReachID") FROM "{0}"."StreamCenterlines";'
        qry = qry.format(self.schema)
        nor = int(self.rgis.rdb.run_query(qry, fetch=True)[0][0])
        if self.rgis.DEBUG:
            self.rgis.addInfo('Nr of reaches: {0:d}'.format(nor))
        return nor

    def number_of_xsections(self):
        qry = 'SELECT COUNT("XsecID") FROM "{0}"."XSCutLines";'
        qry = qry.format(self.schema)
        nox = int(self.rgis.rdb.run_query(qry, fetch=True)[0][0])
        if self.rgis.DEBUG:
            self.rgis.addInfo('Nr of cross-sections: {0:d}'.format(nox))
        return nox

    def spatial_extent(self):
        qry = 'SELECT ST_Extent(geom) FROM "{0}"."XSCutLines";'
        qry = qry.format(self.schema)
        box = self.run_query(qry, fetch=True)[0][0]
        box_min = box[box.index('(')+1:box.index(',')].split()
        box_max = box[box.index(',')+1:box.index(')')].split()
        ext = 'XMIN: {0}\n      YMIN: {1}\n      XMAX: {2}\n      YMAX: {3}\n   '
        ext = ext.format(box_min[0], box_min[1], box_max[0], box_max[1])
        if self.rgis.DEBUG:
            self.rgis.addInfo(ext)
        return ext

    def spatial_unit(self):
        u = self.rgis.crs.mapUnits()
        return QGis.toLiteral(u).upper()

    def build_header(self):
        """
        Return header of RAS GIS Import file.
        """
        hdr = '''#This file is generated by RiverGIS, a QGIS plugin (http://rivergis.com)
BEGIN HEADER:
   DTM TYPE: GRID
   DTM:
   STREAM LAYER: {0}@{1}/{2}/StreamCenterlines
   NUMBER OF REACHES: {3:d}
   CROSS-SECTION LAYER: {0}@{1}/{2}/XSCutLines
   NUMBER OF CROSS-SECTIONS: {4:d}
   MAP PROJECTION:
   PROJECTION ZONE:
   DATUM:
   VERTICAL DATUM:
   BEGIN SPATIAL EXTENT:
      {5}END SPATIAL EXTENT:
      UNITS: {6}
END HEADER:

'''
        hdr = hdr.format(self.dbname, self.host, self.schema, self.nor, self.nox, self.se, self.su)
        return hdr

    def build_network(self):
        # TODO: Rewrite string concatenation way.
        """
        Return STREAM NETWORK part of RAS GIS Import file
        """
        def centerline_points_wkt(wkt):
            res = ''
            pts = wkt[11:-1].split(',')
            for pt in pts:
                res += '{0}{1}, NULL\n'.format(' '*9, ', '.join([c for c in pt.split()]))
            return res

        net = 'BEGIN STREAM NETWORK:\n\n'
        qry = 'SELECT "NodeID", "X", "Y" FROM "{0}"."NodesTable";'
        qry = qry.format(self.schema)
        nodes = self.rgis.rdb.run_query(qry, fetch=True)
        for node in nodes:
            net += '   ENDPOINT: {0:f}, {1:f}, 0, {2}\n'.format(node[1], node[2], node[0])
        qry = 'SELECT "ReachID", "RiverCode", "ReachCode", "FromNode", "ToNode", ST_AsText(geom) FROM "{0}"."StreamCenterlines";'
        qry = qry.format(self.schema)
        reaches = self.rgis.rdb.run_query(qry, fetch=True)
        for reach in reaches:
            net += '\n   REACH:\n      STREAM ID: {0}\n      REACH ID: {1}\n      '.format(reach[1], reach[2])
            net += 'FROM POINT: {:d}\n      '.format(reach[3])
            net += 'TO POINT: {:d}\n      CENTERLINE:\n'.format(reach[4])
            net += centerline_points_wkt(reach[5])
            net += '   END:\n'
        net += '\nEND STREAM NETWORK:\n\n'
        return net

    def build_ras_gis_import(self):
        imp = self.build_header()
        imp += self.build_network()
        return imp