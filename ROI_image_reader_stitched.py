# -*- coding: utf-8 -*-
"""
Created on Mon Jan 29 12:02:08 2018

@author: Darren Henrichs

This file is a first attempt to make an image reader for IFCB data from the raw bytes files. 
"""

from PIL import Image
import os
import numpy as np


def load_data(infilename):
    #will load the data file and adc information file
    inroi = open(infilename + '.roi', 'rb')
    inroi = bytearray(inroi.read())
    inadc = open(infilename + '.adc')
    inadc = [line[:-1] for line in inadc]
    return [inadc, inroi]

def get_image(image_num, indata):
    #will take the image index and the image data and adc files 
    #and get the image, return the image array
    zero_image = 0
    try:
        ###this is for new style IFCB data "D20****"
        image_width = int(indata[0][image_num].split(',')[15])
        image_height = int(indata[0][image_num].split(',')[16])
        start_byte = int(indata[0][image_num].split(',')[17])
        
        try:
            end_byte = int(indata[0][image_num+1].split(',')[17])
            image_bytes = indata[1][start_byte:end_byte]
        except:
            image_bytes = indata[1][start_byte:]
    except:
        try:
            #this is for old style IFCB data
            #the ADC file is different
            image_width = int(indata[0][image_num].split(',')[11])
            image_height = int(indata[0][image_num].split(',')[12])
            start_byte = int(indata[0][image_num].split(',')[13])
            
            try:
                #check if image should be stitched
                if int(indata[0][image_num].split(',')[0]) == int(indata[0][image_num+1].split(',')[0]): #will check to see if next line in ADC file is from same trigger
                    img1_data = indata[0][image_num].split(',')
                    img2_data = indata[0][image_num+1].split(',')
                    
                    img1_upperleftcorner = (int(img1_data[9]), int(img1_data[10])+int(img1_data[12]))
                    img1_lowerrightcorner = (int(img1_data[9])+int(img1_data[11]), int(img1_data[10]))
                    img2_upperleftcorner = (int(img2_data[9]), int(img2_data[10])+int(img2_data[12]))
                    img2_lowerrightcorner = (int(img2_data[9])+int(img2_data[11]), int(img2_data[10]))

                    if int(indata[0][image_num+1].split(',')[10]) < 0:  #if <0 then it doesn't need to be stitched; this only works for 2008 and 2009; 2010 is a different beast
                        end_byte = int(indata[0][image_num+1].split(',')[13])
                        image_bytes = indata[1][start_byte:end_byte]
                    
                    #check to see if corners/edges are away from each other
                    #got this from: https://www.geeksforgeeks.org/find-two-rectangles-overlap/
                    elif img1_upperleftcorner[0] > img2_lowerrightcorner[0] or \
                            img2_upperleftcorner[0] > img1_lowerrightcorner[0] or \
                            img1_upperleftcorner[1] < img2_lowerrightcorner[1] or \
                            img2_upperleftcorner[1] < img1_lowerrightcorner[1]:
                        #images don't overlap, don't need to stitch
                        end_byte = int(indata[0][image_num+1].split(',')[13])
                        image_bytes = indata[1][start_byte:end_byte]
                        
                    else: #it does need to be stitched
                        #adc data is: ROIx, ROIy, ROIwidth, ROIheight, start_byte (for this image)
                        img1_adc = np.array(indata[0][image_num].split(',')[9:14]).astype(np.int32)
                        img2_adc = np.array(indata[0][image_num+1].split(',')[9:14]).astype(np.int32)
                        img1_endbyte = img2_adc[4]
                        try:
                            img2_endbyte = int(indata[0][image_num+2].split(',')[13]) #see if there's an image after this one
                        except:
                            img2_endbyte = -999 #no image after this one; read to end of file

                        #now there are 4 possibilities: 
                        #1) img1 x, y are both closer to origin, 
                        #2) img1 x, img2 y are closer to origin,
                        #3) img1 y, img2 x are closer to origin,
                        #4) img2 x and y are closer to origin

                        #find out which option

                        if img1_adc[0] < img2_adc[0]:
                            #either #1 or #2
                            if img1_adc[1] < img2_adc[1]:
                                #option 1
                                img_origin = (img2_adc[0] - img1_adc[0], img2_adc[1] - img1_adc[1]) 
                                #find max width
                                stitch_width = max(img_origin[0] + img2_adc[2], img1_adc[2])
                                stitch_height = max(img_origin[1] + img2_adc[3], img1_adc[3])
                                zero_image = 1
                            else:
                                #option 2
                                img_origin = (img2_adc[0] - img1_adc[0], img1_adc[1] - img2_adc[1])
                                stitch_width = max(img_origin[0] + img2_adc[2], img1_adc[2])
                                stitch_height = max(img_origin[1] + img1_adc[3], img2_adc[3])
                                zero_image = 2
                        else:
                            if img1_adc[1] < img2_adc[1]:
                                #option 3
                                img_origin = (img1_adc[0] - img2_adc[0], img2_adc[1] - img1_adc[1])
                                stitch_width = max(img_origin[0] + img1_adc[2], img2_adc[2])
                                stitch_height = max(img_origin[1] + img2_adc[3], img1_adc[3])
                                zero_image = 3
                            else:
                                #option 4
                                img_origin = (img1_adc[0] - img2_adc[0], img1_adc[1] - img2_adc[1])
                                stitch_width = max(img_origin[0] + img1_adc[2], img2_adc[2])
                                stitch_height = max(img_origin[1] + img1_adc[3], img2_adc[3])
                                zero_image = 4
                        out_image = np.zeros((stitch_width, stitch_height)).astype(np.int32)
                else:
                    end_byte = int(indata[0][image_num+1].split(',')[13])
                    image_bytes = indata[1][start_byte:end_byte]
            except:
                image_bytes = indata[1][start_byte:]
        
        except:
            image_width = 0
            image_height = 0
            
    stitched = False #set flag

    if image_width == image_height == 0:
        image = None
    elif zero_image == 0:
        image = Image.frombytes(mode='L', size=(image_width, image_height), data=bytes(image_bytes))
    else: #return stitched image
        image1 = Image.frombytes(mode='L', size=(img1_adc[2], img1_adc[3]), data=bytes(indata[1][img1_adc[4]:img2_adc[4]]))
        if img2_endbyte == -999:
            image2 = Image.frombytes(mode='L', size=(img2_adc[2], img2_adc[3]), data=bytes(indata[1][img2_adc[4]:]))
        else:
            image2 = Image.frombytes(mode='L', size=(img2_adc[2], img2_adc[3]), data=bytes(indata[1][img2_adc[4]:img2_endbyte]))

        out_image = np.zeros((stitch_height, stitch_width)).astype(np.int32)
        image1 = np.array(image1)
        image2 = np.array(image2)
        out_image[:,:] = int(image1[:3,:3].mean()) #fill in with background color
        if zero_image == 1:
            out_image[:img1_adc[3], :img1_adc[2]] = image1
            out_image[img_origin[1]:img_origin[1]+img2_adc[3], img_origin[0]:img_origin[0]+img2_adc[2]] = image2
        elif zero_image == 2:
            out_image[img_origin[1]:img_origin[1]+img1_adc[3], :img1_adc[2]] = image1
            out_image[:img2_adc[3], img_origin[0]:img_origin[0]+img2_adc[2]] = image2
        elif zero_image == 3:
            out_image[:img1_adc[3], img_origin[0]:img_origin[0]+img1_adc[2]] = image1
            out_image[img_origin[1]:img_origin[1]+img2_adc[3], :img2_adc[2]] = image2
        else:
            out_image[img_origin[1]:img_origin[1]+img1_adc[3], img_origin[0]:img_origin[0]+img1_adc[2]] = image1
            out_image[:img2_adc[3], :img2_adc[2]] = image2
        image = Image.fromarray(out_image)
        stitched = True

    return image, stitched
    
def process_file(infilename, num_images=-1, start_image=0):
    #go through the images in the file, can all images or a few, can start
    #at beginning or jump to an image
    loaded_images = [] #this will hold all of the images in case you don't want 
                # them written to disk
    indata = load_data(infilename)
    
    #loaded_images is a list of images each containing [roi_num, image_itself]
    
    if num_images == -1:
        num_images = len(indata[0])
    stitched = False
    for indiv_image in range(0+start_image, len(indata[0][start_image:start_image+num_images])):
        if stitched:
            stitched = False
            continue
        temp_image = get_image(indiv_image, indata)
        image_result = [indiv_image+1, temp_image[0]]
        if image_result[1] is not None:
            loaded_images.append(image_result)
        if temp_image[1] == True:
            stitched = True
    
    return loaded_images
        
def load_data_file(inpath):
	processed_images = []
	list_of_files = os.listdir(inpath)
	
	list_of_files = [filename[:-4] for filename in list_of_files] #shave the file extension and period
	list_of_files = list(set(list_of_files))
	
	for indiv_file in list_of_files[0:1]:
		processed_images.append([indiv_file, process_file(inpath + indiv_file)])
    
	return processed_images

processed_images = []

def main():
    list_of_files = os.listdir(datapath)
    list_of_files = [filename[:-4] for filename in list_of_files] #shave the file extension and period
    list_of_files = list(set(list_of_files))
    
    #processed_images = []
    for indiv_file in list_of_files[0:1]:
        print(indiv_file)
        processed_images.append([indiv_file, process_file(datapath + indiv_file)])
    
