#!usr/bin/env python

#===============================================================================
# Import modules
#===============================================================================
# Standard Library
import os
import sys
import datetime
import time
import collections
import json

# Third party modules

# Application modules
import airtable.airtable as airtable
import toolbox.log as log
import logging
import toolbox.check_process as check_process


#---------------------------------------------------------------------------
# Nested dictionaries
#---------------------------------------------------------------------------
def nested_dict():
    return collections.defaultdict(nested_dict)



#===============================================================================
# MAIN
#===============================================================================
def main():
    
    '''
    Passed arguments:
        --syncerr     - disables reporting of sync errors 
    '''

    script_name = os.path.basename(sys.argv[0])
    folder_loc  = os.path.dirname(os.path.realpath(sys.argv[0]))
    folder_loc  = folder_loc.replace('scripts', '')
    folder_root = folder_loc.replace('/garden-airtable/', '')

    
    #---------------------------------------------------------------------------
    # Set up logger
    #---------------------------------------------------------------------------
    logger = log.setup('root', '{folder}/logs/{script}.log'.format(
                                                    folder= folder_loc,
                                                    script= script_name[:-3]))
    
    logger.info('')
    logger.info('--- Script {script} Started ---'.format(script= script_name)) 

    
    #---------------------------------------------------------------------------
    # CHECK SCRIPT IS NOT ALREADY RUNNING
    #---------------------------------------------------------------------------    
    if check_process.is_running(script_name):
        logger.error('Script already running.')
        sys.exit()
            
    try:       
        #-------------------------------------------------------------------
        # Check and action passed arguments
        #-------------------------------------------------------------------
        sync_err = False
        if len(sys.argv) > 1:
            if '--syncerr' in sys.argv:
                logger.info('User requested NO ERROR feedback.')
                sync_err = True
 

        #-------------------------------------------------------------------
        # Get data from config file
        #-------------------------------------------------------------------  
        with open('{fl}/data/config.json'.format(fl= folder_loc), 'r') as f:
            config = json.load(f)

        at_api_key      = config['airtable']['API_KEY']
        at_base_id      = config['airtable']['BASE_ID']
        at_garden_plants = config['airtable']['TABLE_NAME']['GARDEN_PLANTS']

        
        #-------------------------------------------------------------------
        # Set up airtable API
        #------------------------------------------------------------------- 
        at = airtable.Airtable(at_base_id, at_api_key)

 
        #-------------------------------------------------------------------
        # Get garden data from file
        #-------------------------------------------------------------------
        with open('{fl}/garden-evernote/data/gardening_web.json'.format(fl= folder_root), 'r') as f:
            data = json.load(f)

        garden_plants = data['diary']
        names = data['plant_tags']
        locs = data['location_tags']
        

        #-------------------------------------------------------------------
        # Download airtable data
        #-------------------------------------------------------------------
        logger.info('Downloading data from airtable...')
        at_plants = nested_dict()
        recs_to_delete = []
        
        offset = None
        i=0
        while True:
            response = at.get(at_garden_plants, offset=offset)
            for record in response.pop('records'):
                keys = record['fields'].keys()

                if 'Plant ID' not in keys: 
                    recs_to_delete.append(record['id'])
                    continue

                p_id = str(record['fields']['Plant ID'])
                p_n = unicode(float(record['fields']['Number']))

                at_plants[p_id][p_n] = {
                    'Location': record['fields']['Location'],
                    'Name': record['fields']['Name'],
                    'Id': record['id']
                }

                if 'Alive' in keys:
                    at_plants[p_id][p_n]['Alive'] = record['fields']['Alive']
                else:
                    at_plants[p_id][p_n]['Alive'] = False
                    

                if 'Variety' in keys:
                    at_plants[p_id][p_n]['Variety'] = record['fields']['Variety']

                i+=1

            if 'offset' in response:
                logger.info('Still downloading...')
                offset = str(response['offset'])
            else:
                break

        logger.info('DONE. {n} records downloaded.'.format(n=i))

        with open('{fl}/data/tabledata.json'.format(fl= folder_loc), 'w') as f:
           json.dump(at_plants, f)

        
        #-------------------------------------------------------------------
        # Remove records in airtable and not in garden
        #-------------------------------------------------------------------
        id_to_remove = set(at_plants.keys()) - set(garden_plants.keys()) 
        recs_to_delete = recs_to_delete + [at_plants[plant_id][n]['Id'] for plant_id in id_to_remove for n in at_plants[plant_id].keys()]
            
        for rec in recs_to_delete:    
            logger.info('Removing: {c}'.format(c=rec))
            response = at.delete(str(at_garden_plants), str(rec))
            if 'error' in response.keys(): raise Exception(response['error']['message'])
            

        #-------------------------------------------------------------------
        # Sync garden data with airtable data
        #-------------------------------------------------------------------
        for plant_id in garden_plants:

            rec = {'Plant ID': plant_id}

            if " '" in names[plant_id]:
                # Remove # fron the begining of the name and the last quote
                full_name = names[plant_id][1:-1].split(" '")
                rec['Name'] = full_name[0]
                rec['Variety'] = full_name[1]
            else:
                rec['Name'] = names[plant_id][1:]

            ns = set([n for n in garden_plants[plant_id].keys()])
            at_ns = set(at_plants[plant_id].keys())
            all_plant_numbers = ns | at_ns

            for n in all_plant_numbers:
                response = {}

                # Remove extra plants
                if n not in ns:
                    logger.info('Removing: {c} - {no}'.format(c=names[plant_id][1:], no=n))
                    response = at.delete(str(at_garden_plants), str(at_plants[plant_id][n]['Id']))
                    continue

                rec['Location'] = locs[garden_plants[plant_id][n]['location']][1:]
                rec['Number'] = float(n)
                rec['Alive'] = garden_plants[plant_id][n]['alive']

                # Add missing plants
                if n not in at_ns:
                    logger.info('Not in db: {c} - {no}'.format(c=names[plant_id][1:], no=n))
                    response = at.create(str(at_garden_plants), rec)
                    continue

                # Check for incorrect values
                rk = at_plants[plant_id][n].keys()
                rk.remove('Id')
                if any([True for k in rk if rec[k] != at_plants[plant_id][n][k]]):
                    logger.info('Updating: {c} - {no}'.format(c=names[plant_id][1:], no=n))
                    response = at.update(str(at_garden_plants), str(at_plants[plant_id][n]['Id']), rec)

                if 'error' in response.keys():
                    raise Exception(response['error']['message'])

                # Slow loop down not to exceed api rate limit
                elif response:
                    time.sleep(12)
            
    except Exception, e:
        logger.error('Update failed ({error_v}). Exiting...'.format(
            error_v=e), exc_info=True)
        sys.exit()
        
    finally:
        logger.info('--- Script Finished ---')



#===============================================================================
# Boiler plate
#===============================================================================
if __name__=='__main__':
    main()
