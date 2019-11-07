"""
@author: laurendelong
"""
import urllib.request
import os
import json
import bz2
import re
from dataclasses import dataclass
from typing import List
import itertools
import sqlite3

conn = sqlite3.connect('dbsnp.db')
c = conn.cursor()


@dataclass
class SnpInfo:
    dbsnp_id: str
    assembly_id: str
    gen_type: str
    gene_name: str
    gene_abbr: str
    gene_id: str
    dna_change: List[str]
    rnas: str
    rna_type: str
    rna_change: List[str]
    proteins: str
    prot_type: str
    aa_change: List[str]

def snpid2table(list):
    t = list
    c.executemany(
        'INSERT INTO dbsnp_id_MT VALUES (?)', t
    )
    conn.commit()

def snpdna2table(list):
    t = list
    c.executemany(
        'INSERT INTO dna_change_MT VALUES (?,?)', t
    )
    conn.commit()


def main():
    # Here we begin the downloading of JSON files from the dbSNP database:

    # Create tables
    c.execute('CREATE TABLE dbsnp_id_MT (dbsnp_id)')
    c.execute('CREATE TABLE dna_change_MT (dna_change, dbsnp_id)')

    url = 'ftp://ftp.ncbi.nih.gov/snp/latest_release/JSON/refsnp-chrMT.json.bz2'
    path = '/home/llong/Downloads/refsnp/refsnp-chrMT.json.bz2'
    if not os.path.exists(path):
        print('Beginning file download with urllib2...')
        urllib.request.urlretrieve(url, path)
        print('...Finished file download with urllib2.')

    id_list = []
    dna_change_list = []

    # Here we parse through the files:
    print('Now decompressing and reading JSON.bz2 files with *bz2* and *json* ...')
    with bz2.BZ2File(path, 'rb') as f_in, \
            open('/home/llong/Downloads/refsnp/refsnp-chrMT.csv', 'w') as output:
        for line in f_in:
            rs_obj = json.loads(line.decode('utf-8'))
            dbsnp_id = rs_obj['refsnp_id']  # the dbsnp id
            # Make the dbsnp_id table for database
            id_list.append((dbsnp_id,))

            all_ann_list_raw = rs_obj['primary_snapshot_data'][
                'allele_annotations']  # these are the assembly annotations

            if len(all_ann_list_raw) >= 2:  # if it has sufficient info
                assembl_ann_list_raw = all_ann_list_raw[1]['assembly_annotation']  # against each assembly
                if len(assembl_ann_list_raw) != 0:  # if it contains gene info
                    gene_list_raw = assembl_ann_list_raw[0][
                        'genes']  # and each of the genes affected within each assembly
                    if len(gene_list_raw) > 0:
                        # Here I start extracting gene info:
                        for x, y, z in itertools.product(range(len(all_ann_list_raw)),
                                                         range(len(assembl_ann_list_raw)),
                                                         range(len(gene_list_raw))):
                            assembly_id = all_ann_list_raw[x]['assembly_annotation'][y]['seq_id']

                            gene_name = all_ann_list_raw[x]['assembly_annotation'][y]['genes'][z]['name']
                            gene_abbr = all_ann_list_raw[x]['assembly_annotation'][y]['genes'][z]['locus']
                            gene_id = all_ann_list_raw[x]['assembly_annotation'][y]['genes'][z]['id']
                            rna_list_raw = all_ann_list_raw[x]['assembly_annotation'][y]['genes'][z]['rnas']

                            for nuc in rna_list_raw:
                                # Here I parse through each hgvs entry and assign it to either a nuc. change or a.a. change
                                hgvs_entries = rs_obj['primary_snapshot_data']['placements_with_allele']
                                dna_change = []
                                aa_change = []
                                rna_change = []
                                for entry in hgvs_entries:
                                    for variant in entry['alleles']:
                                        hgvs = re.split(":[cgmnopr].", variant['hgvs'])
                                        if len(hgvs) > 1:
                                            if hgvs[0] == assembly_id:
                                                dna_change.append(hgvs[1])
                                                # Here I make the DNA change table
                                                dna_change_list.append((hgvs[1], dbsnp_id))
                                            else:
                                                continue

    snpid2table(id_list)
    snpdna2table(dna_change_list)
    print("Finished writing files to database")
    conn.close()


if __name__ == '__main__':
    main()