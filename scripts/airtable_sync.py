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
        # Sync plant names
        #-------------------------------------------------------------------
        with open('{fl}/garden-evernote/data/gardening_web.json'.format(fl= folder_root), 'r') as f:
            data = json.load(f)

        plants = data['diary']
        names = data['plant_tags']
        locs = data['location_tags']
        
        logger.info('Downloading data from airtable...')
        at_plants = at.get(at_garden_plants)
        logger.info('DONE.')
        with open('{fl}/data/tabledata.json'.format(fl= folder_loc), 'w') as f:
           json.dump(at_plants, f)
        # with open('{fl}/data/tabledata.json'.format(fl= folder_loc), 'r') as f:
        #     at_plants = json.load(f)

        at_plants_id = [str(p['fields']['Plant ID']) for p in at_plants['records']]

        year_current = datetime.datetime.now().year

        for plant_id in plants:
            ns = plants[plant_id].keys()
            for n in ns:
                if not plants[plant_id][n]['alive']: continue

                rec = {
                        'Number': float(n),
                        'Location': locs[plants[plant_id][n]['location']][1:],
                        'Plant ID': plant_id
                    }

                if " '" in names[plant_id]:
                    # Remove # fron the begining of the name and the last quote
                    full_name = names[plant_id][1:-1].split(" '")
                    rec['Name'] = full_name[0]
                    rec['Variety'] = full_name[1]
                else:
                    rec['Name'] = names[plant_id][1:]

                response = {}

                if plant_id not in at_plants_id:
                    logger.info('Not in db: {c} - {no}'.format(c=names[plant_id][1:], no=n))
                    response = at.create(str(at_garden_plants), rec)

                elif plant_id in at_plants_id:
                    for p in at_plants['records']:
                        if str(p['fields']['Plant ID']) == plant_id and p['fields']['Number'] == float(n):
                            rk = rec.keys()
                            rk.remove('Number')
                            pk = p['fields'].keys()

                            update = False
                            # Check if all items are present
                            if any([True for k in rk if k not in pk]):
                                update = True
                            
                            # Check if all item values are the same
                            elif any([True for k in rk if str(rec[k]) != str(p['fields'][k])]):
                                update = True

                            if update:
                                response = at.update(str(at_garden_plants), str(p['id']), rec)
                                logger.info('Updated: {c} - {no}'.format(c=names[plant_id][1:], no=n))
                                break

                if 'error' in response.keys():
                    logger.error(response['error']['message'])
                    sys.exit()
                
                # Slow loop down not to exceed api rate limit
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
