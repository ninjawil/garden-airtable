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
        at_garden_plants = str(config['airtable']['TABLE_NAME']['GARDEN_PLANTS'])
        at_varieties    = str(config['airtable']['TABLE_NAME']['VARIETIES'])
        at_plants       = str(config['airtable']['TABLE_NAME']['PLANTS'])

        
        #-------------------------------------------------------------------
        # Set up airtable API
        #------------------------------------------------------------------- 
        at = airtable.Airtable(at_base_id, at_api_key)

        
        #-------------------------------------------------------------------
        # Sync plant names
        #-------------------------------------------------------------------
        with open('{fl}/garden-evernote/data/gardening.json'.format(fl= folder_root), 'r') as f:
            data = json.load(f)

        plants = data['plant_tags']

        at_plants = at.get(at_plants)
        at_plants = [str(p['fields']['Name']) for p in at_plants['records']]
        print type(at_plants[0])

        for key in plants:
            if '\"' in plants[key]:
                # Remove # fron the begining of the name and the last quote
                plant = plants[key][1:-1].split(' "')

                name = str(plant[0])
                name_common = str(plant[1])
                
                if name not in at_plants:
                    rec = {
                        'Name': name,
                        'Common Name': name_common
                        }
                    test = at.create(at_plants, rec)

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
