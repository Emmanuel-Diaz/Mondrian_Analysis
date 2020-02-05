import requests
import os
from bs4 import BeautifulSoup
import re
from collections import defaultdict
import collections
import random
import json
import sys

"""
Scrapes artwork from Catalogue Raisonné of Mondrian's collection
Params: link - Page to scrape from
        art_ids - list of ids to label artwork
"""
def scrape_raisonne_page(link, art_ids):
    
    #Get Raisonne Webpage
    result = requests.get(link)
    
    # if successful parse the download into a BeautifulSoup object, which allows easy manipulation 
    if result.status_code == 200:
        soup = BeautifulSoup(result.text, "html.parser")
        
    #Store image links and metadata
    images = defaultdict(list)
    random.shuffle(art_ids)
    
    #Go through each painting container
    for tab in soup.find_all('table', {'class':'area'}):
        
        #Go through each table
        for t in tab.find_all('tr'):
            
            #Get image id
            curr_id = art_ids.pop(0)

            #Get large image
            #class - 'image-large', 'image-thumb'
            span_url = t.find('span',{'class':'image-large'})

            #Skip if span_url doesn't exist
            if not span_url:
                continue
                
            #Grab image url
            image_url = span_url.find('img')['src']

            #Metadata collection
            description = t.find('div',{'class':'image-description'})
            
            if description == None:
                painting_desc = "NA"
                year = -1
            else:
                if description.find('b')==None:
                    painting_desc = "None"
                else:
                    painting_desc = description.find('b').string
                    
                if len(re.findall(r'\d+', description.text))==0:
                    year = -1
                else:
                    year=re.findall(r'\d+', description.text)[0]
            
            #Find width/height of image
            width_m = re.search('width=(\d+)', image_url)
            height_m = re.search('height=(\d+)', image_url)  
            width = width_m.group(1) if width_m else 0
            height = height_m.group(1) if height_m else 0

            #Store this painting
            images[year].append({"url":image_url, "written_desc":painting_desc, "year":year,"dimension":(width,height), "img_id":curr_id, "src_id":1})
        
    return images


"""
Gets next page of artwork to scrape for scrape_raisonne_page
Params: link - Link to current Raisonne page
Returns: Link to next page to scrape, empty string if no more pages to scrape
"""
def raisonne_next_page(link):
    
    STOP_PAGE = "http://pietmondrian.rkdmonographs.nl/copies-c154-c155"
    
    #Get Raisonne Webpage
    result = requests.get(link)

    # if successful parse the download into a BeautifulSoup object, which allows easy manipulation 
    if result.status_code == 200:
        soup = BeautifulSoup(result.text, "html.parser")
        
    #Get page markers
    markers = soup.find('ul', {'class':'portletNavigationTree navTreeLevel0'})
    markers = markers.find_all('li')
    
    found_next_link = False
    for m in markers:
        
        next_link = m.find('a')['href']
        
        #Found next link to scrape
        if found_next_link:
            return next_link
        
        #Stopping condition page
        if next_link == STOP_PAGE:
            return ""
        
        #Found current link
        if link == next_link:
            found_next_link = True
            continue
                
    return ""


"""
Downloads and writes image to disk
Params: img_link - Link to image to be downloaded
        img_id - id of image to write to disk
        outpath - directory to write image to
"""
def download_image(img_link, img_id, outpath):
    
    #Get image
    page = requests.get(img_link)
    
    #Create outpath directory if doesn't exist
    if not os.path.exists("./"+outpath):
        os.mkdir("./"+outpath)

    #Get file extension
    f_ext = os.path.splitext(img_link)[-1]
    if ".jpg" in f_ext:
        f_ext = ".jpg"
    elif ".png" in f_ext:
        f_ext = ".png"
    elif ".jpeg" in f_ext:
        f_ext='.jpeg'
        
    #Create file path
    final_file = os.path.join(outpath, "img{0}{1}".format(str(img_id),".csv"))
        
    #Write as csv and save extension
    with open(final_file, 'wb') as f:
        f.write(f_ext)
        f.write(page.content)



"""
Takes JSON config structured as such
{

    'years':[{'url':, 'metadata'}],
    'outpath': outpath
    
}
"""
def proccess_config(years, outpath):
    #Downloads all images to path
    for y in years:
        download_image(y['url'], y['img_id'], outpath)  
    return 1


"""
Gets Mondrian's work from Catalogue Raisonné

Returns: Dictionary with year as key, art data as values
"""
def scrape_mondrian_artwork():
    
    artwork = defaultdict(list)
    
    raisonne_link = "http://pietmondrian.rkdmonographs.nl/copy_of_winterswijk-i-before-circa-1897-a1-a22"
    
    #Get random collection of art_ids to label artwork
    art_ids = random.sample(range(15000), 10000)
    
    next_link = raisonne_link
    out = scrape_raisonne_page(next_link, art_ids)

    #Iterate while output of scraping exists
    while out:
        out = scrape_raisonne_page(next_link, art_ids)
        
        #Add page's art to collection of years
        for key,value in out.items():
            artwork[key].extend(value)
            
        #Get next page for scraping
        next_link = raisonne_next_page(next_link)
        if next_link == "":
            break
            
    return artwork 


"""
Params: art - artwork collection dictionary returned from scrape_mondrian_artwork()
        outpath - directory to write images to
"""
def save_images(art,outpath):
    
    #Go through all years
    for key, value in art.items():
        
        #Go through all art pieces
        for art_piece in art[key]:
            
            #Download and save art_piece
            download_image(art_piece['url'], art_piece['img_id'], outpath)
    return

"""
Params: art - artwork collection dictionary returned from scrape_mondrian_artwork()
        outpath - directory to write config to
"""
def save_config(art, outpath):
    #Create outpath directory if doesn't exist
    if not os.path.exists("./"+outpath):
        os.mkdir("./"+outpath)
        
    final_json = os.path.join(outpath, "scraped_config{}".format(".json"))
    
    with open(final_json, 'w') as f:
        json.dump(art, f)