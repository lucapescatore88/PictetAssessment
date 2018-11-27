from engineutils import loadCurrencies, cleanData
from engineutils import country_df, resroot, NAval, convertToUSD
from networthutils import parseNetWorth
from HTMLParser import HTMLParser
from unidecode import unidecode
from bs4 import BeautifulSoup
from datetime import datetime
import wikipedia, requests
import pandas as pd
import re, os

## Initial lodings

wikipedia.set_lang("en")
hparse = HTMLParser()

### Find the Profession

def findWikiProfession(soup) :

    tags = ["Occupation","Profession"]
    professions = []
    for tr in soup.findChildren("tr") :
        
        found = False
        for th in tr.findChildren("th") :
            if th.string in tags : 
                found = True 
                break

        if not found : continue
        #print "Found Profession tag!"

        for li in tr.findChildren("li") :
            links =  li.findChildren("a")
            prof = li.string
            if len(links)>0 : prof = links[0].string
            professions.append(hparse.unescape(prof))
        
        if len(professions)==0 : 
            data = tr.findChildren("td")[0].__str__()
            data = hparse.unescape(data)
            data = re.sub(r"(?i)<br/>","",data)
            data = re.sub(r"(?i)<[/]?a.*?>","",data)
            data = re.sub(r"(?i)<[/]?[ibp]>","",data)
            data = re.sub(r"(?i)<[/]?tr>","",data)
            data = re.sub(r"(?i)<[/]?td>","",data)
            data = re.sub(r"(?i)<br/>","",data)
            data = re.sub(r"<td class=\"role\">","",data)
            professions.append(data)
        break
    return professions


### Find the Nationality

strangepeople = ["ENGLISH","SCOTTISH","WELSH"]

def unstrange(nat) :
    if nat in strangepeople : 
        return "BRITISH"
    return nat

def findNationality(text) :

    cleantext = re.sub(r'\0xe2|\0xc3|\\s+'," ",text).lower()
    
    nationalities = country_df['Nationality'].tolist() ## List of nationalities to compare against
    nationalities.extend(strangepeople)
    countries = country_df['Name'].tolist() ## List of countries to compare against

    for nat in nationalities :
        if nat.lower() in cleantext :
            return unstrange(foundnat)

    for country in countries :
        if country.lower() in cleantext :
            countryinfo = country_df.loc[country_df['Name'] == country]
            return unstrange(countryinfo['Nationality'].values[0])

    return NAval


def findWikiNationality(soup,bio=None,fulltext=None) :
    
    ## Find in infobox
    for tr in soup.findChildren("tr") :
        
        found = False
        for th in tr.findChildren("th") :
            if th.string == "Nationality" : 
                found = True 
                break

        if not found : continue
        
        td = tr.findChildren("td")[0]
        if td.string.upper() in strangepeople : return "BRITISH"
        return str(td.string)

        break

    ## Find in biography

    if bio is not None :
        nat = findNationality(bio)
        if nat is not None : return nat

    ## Find in full Wiki page: just returns first nation or nationality found
    ## Could add scoring to return most represented nationality 
    if fulltext is not None :
        return findNationality(fulltext)

    return NAval


### Find the Date of Birth

def findWikiBirthDay(soup,bio=None) :

    ## Find in infobox
    for el in soup.findChildren("span",{'class':'bday'}) :
        return el.text

    ## Find in biography
    if bio is not None :

        #print "Looking for birthday in biography"
        match = re.match("(?i)\\(.*?born.*?(\\d{4}).*?\\)",bio)
        
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dic']
        patts = [ '%s.*?\\d{4}' % mon for mon in months ]
        patt = '(?i)\\(.*?born.*?('+'|'.join(patts)+').*?\\)'
        match = re.match(patt,bio)
        if match is not None : return match.groups()[0] 

        # Try only year
        match = re.match("(?i)\\(.*?born.*?(\\d{4}).*?\\)",bio)
        if match is not None : return match.groups()[0] 

    return NAval


def parseBirthday(bday) :

    if bday == NAval : 
        return (-1, -1, -1)

    dateobj = None
    day, month, year = -1, -1, -1
    try :
        dateobj = datetime.strptime(bday,'%Y-%m-%d')
    except Exception as e:
        #print (e)
        try :
            dateobj = datetime.strptime(bday,'%B %d, %Y')
        except : pass #Exception as e: print (e)
    
    if dateobj is None :
        match = re.match(".*?(\\d{4}).*?",bday)
        if match is not None :
            year = int(match.groups()[0])
    else :
        day, month, year = dateobj.day, dateobj.month, dateobj.year

    return (day, month, year)


### Find how rich they are

def getNetWorthTag(soup) :

    for tr in soup.findChildren("tr") :
        for th in tr.findChildren("th") :
            if th.string == "Net worth" : 
                return tr

def findWikiNetWorth(soup) :

    money = -1
    tr = getNetWorthTag(soup)

    if tr is None : return money
    
    content = tr.__str__().lower().decode("utf8")
    money = float(re.findall("\\d+\\.\\d+",content)[0])    ## Getting value
    if 'billion' in content :
        money *= 1000

    return convertToUSD(money,content)


## Find the biography 

def findWikiBiography(soup,name,surname) :

    bio = None
    names = ""

    ## Biography always contains a <b> tag containin the person name
    ## This also contains the full name! So can obtain the middle name
    for p in soup.findChildren("p") :
        found = False
        for b in p.findChildren("b") :
            if surname in b.string :
                bio = p
                names = b.string.replace(name,"")
                names = names.replace(surname,"")
                names = names.lstrip().rstrip()
                found = True
        if found : break

    if bio is None : return NAval, NAval
    
    bio = re.sub(r"(?i)<[/]?[ibp]>","",bio.__str__())   # Remove p,i,b tags
    bio = re.sub(r"(?i)<sup.*?/sup[ ]*>","",bio)        # Remove citations
    bio = re.sub(r"(?i)<[/]?a.*?>","",bio)              # Remove links (but not their text)
    bio = re.sub(r"(?i)<span.*?/span[ ]*>","",bio)
    bio = re.sub(r"(?i)<small.*?/small[ ]*>","",bio)
    bio = hparse.unescape(bio)

    return names, bio

def parseWiki(name,surname,midname="",country="") :
    
    query = '{name} {midname} {surname} {country}'.format(
                name    = name, 
                midname = midname,
                surname = surname,
                country = country ).replace("\\s+"," ")

    pages = wikipedia.search(query)

    mainpage = pages[0] 
    if(name in mainpage and surname in mainpage) :
        page = wikipedia.page(mainpage)
    else :
        print "Something is wrong... no Wiki page found"
        return {'name' : name,'surname': surname,'midname': NAval,
                'bio'  : NAval, 'profession' : NAval,'bday': NAval,
                'money': -1,'country': NAval, "hasSites" : False}

    req = requests.get(page.url)
    mytext = ''.join([i if ord(i) < 128 else ' ' for i in req.text])
    soup = BeautifulSoup(mytext)

    ### Do some extra processing
    midname, bio = findWikiBiography(soup,name,surname)
    if bio is None : bio = NAval
    profs = findWikiProfession(soup)
    if profs is not None : profs = ', '.join(profs)
    else : profs = NAval
    
    bday = findWikiBirthDay(soup,bio)
    day, month, year = parseBirthday(bday)
    networth = findWikiNetWorth(soup)
    nation   = findWikiNationality(soup,bio,mytext)
    
    ## Prepare output
    out = {
        'name'       : name, 'surname' : surname, 'midname' : midname,
        'bio'        : bio, 'profession' : profs,
        'bday'       : bday, 'day' : day, 'month' : month, 'year' : year,
        'money'      : int(networth), 'country'    : nation
    }

    ## Try NetWorth website which have some more money info for rich people
    if networth == -1  or nation == NAval or profs == NAval : 
        out = parseNetWorth(name,surname,out)

    ### If not famous people websites are found set hasSites flag
    out["hasSites"] = True
    if networth == -1  and nation == NAval and profs == NAval and bio == NAval :
        out["hasSites"] = False

    return out



if __name__ == '__main__':

    from engineutils import getPeopleData, trainparser
    import pickle
    
    args = trainparser.parse_args()

    wikidata = getPeopleData("WikiData",args.trainfile,
                        myfunction=parseWiki,
                        usebackup=args.usebackup,
                        save=True)

    entries = []
    for key,dat in wikidata.iteritems() :

        d = {}
        d['isPol'] = key[2]
        d['isFam'] = key[3]
        d.update(dat)
        entries.append(d)

    df = pd.DataFrame.from_dict(entries)
    with open(resroot+"WikiDF.pkl","w") as of :
        pickle.dump(df,of)
    print "Done! The DataFrame is in ", resroot+"WikiDF.pkl"

