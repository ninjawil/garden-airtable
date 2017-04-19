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
        
        at_plants = at.get(at_garden_plants)
        at_plants = [str(p['fields']['Name']) for p in at_plants['records']]

        year_current = datetime.datetime.now().year

        for key in plants:
            ns = plants[key].keys()
            for n in ns:
                year = unicode(str(year_current), "utf-8")

                print year
                print plants[key][n]['timeline'].keys()

                if year not in plants[key][n]['timeline'].keys():
                    continue

                print n

                week = 52
                while week >= 0:
                    if plants[key][n]['timeline'][year][week] is not None:
                        print names[key]
                        break
                    elif week == 0:
                        week = 52
                        year = unicode(str(year_current-1), "utf-8")
                    else:
                        week -=1


        sys.exit()
        if ' "' in plants[key]:
            # Remove # fron the begining of the name and the last quote
            plant = plants[key][1:-1].split(' "')

            try:
                name = str(plant[0])
                name_common = str(plant[1])
            except Exception, e:
                logger.error('Error with tag {p} ({error_v})'.format(
                    p=plant, error_v=e), exc_info=True)  
                # continue

            if name not in at_plants:
                i+=1
                logger.info('Not in db: "{c}"'.format(n=name, c= name_common))
                rec = {
                    'Name': name,
                    'Common Name': name_common
                    }
                # test = at.create(str(at_plants), rec)

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
