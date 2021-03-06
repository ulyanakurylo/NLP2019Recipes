from fractions import Fraction
import os
import platform
import random
import ssl
import sys
from urllib.request import urlopen

from bs4 import BeautifulSoup
from measurement.measures import Volume, Weight
from measurement.utils import guess
import spacy

ssl._create_default_https_context = ssl._create_unverified_context
debug = False

base_url = 'https://www.allrecipes.com/recipe/'
urls = [
    # Random URl
    # If random recipe DNE or has been deleted, AllRecipes will default to:
    # Johnsonville® Three Cheese Italian Style Chicken Sausage Skillet Pizza
    '-1',                 # 0. Random
    # Test URLs
    base_url + '18511',   # 1. Hash Brown Casserole II
    base_url + '212721',  # 2. Indian Chicken Curry (Murgh Kari)
    base_url + '91192',   # 3. French Onion Soup Gratinee
    base_url + '60598',   # 4. Vegetarian Korma
    base_url + '240425',  # 5. Dutch Oven Vegetable Beef Soup
    base_url + '258077',  # 6. Soondubu Jjigae (Korean Soft Tofu Stew)
    base_url + '262353',  # 7. Buffalo Tofu Wings
    base_url + '242352',  # 8. Greek Lemon Chicken and Potatoes
    base_url + '25333',   # 9. Vegan Black Bean Soup
    base_url + '215012'   # 10. Spicy Tuna Fish Cakes
    ]
# AllRecipes URL to parse
url = None
# The HTML parsed by BeautifulSoup
soup = None
recipe_name = ''
ingredients = {}

# If a verb is in this list, we consider it a cooking action
cooking_verbs = [
    'bake', 'barbeque', 'baste', 'batter', 'beat', 'blanch', 'blend', 'boil',
    'broil', 'caramelize', 'carmelize', 'chop', 'cook', 'clarify', 'cream',
    'cure', 'deglaze', 'degrease', 'dice', 'dissolve' 'dredge', 'drizzle',
    'dust', 'fillet', 'flake', 'flambe', 'fold', 'fricasse', 'fry', 'garnish',
    'glaze', 'grate', 'grind', 'julienne', 'knead', 'marinate', 'melt',
    'meuniere', 'mince', 'mix', 'pan-broil', 'pan-fry', 'parboil', 'pare',
    'peel', 'pickle', 'pit', 'plump', 'poach', 'preheat', 'puree', 'refresh',
    'roast', 'saute', 'scald', 'scallop', 'score', 'sear', 'season', 'serve',
    'shred', 'sift', 'simmer', 'skim', 'spread', 'sprinkle', 'steam', 'steep',
    'sterilize', 'stew', 'stir', 'toss', 'truss', 'whip'
    ]
# Used to resolve ties
primary_verbs = [
    'bake', 'roast', 'simmer', 'fry', 'saute', 'steam', 'stew', 'boil'
]
# Exclude conjugations of "to be" no matter what
to_be_verbs = [
    'be', 'is', 'are', 'was'
    ]
# If a word is in this list, we consider it a measurement unit.
measurements_list = [
    # Unique Collections
    'bunch', 'can', 'clove', 'pinch', 'slice', 'sprig', 'rib',
    # Volumes
    'tsp', 'teaspoon', 'tbsp', 'tblsp', 'tbs', 'tablespoon', 'c', 'cup', 'pt', 'pint', 'qt', 'quart', 'gal', 'gallon',
    'ml', 'mL', 'milliliter', 'millilitre', 'l', 'L', 'liter', 'litre',
    # Weights
    'oz', 'ounce', 'lb', 'pound',
    'mg', 'milligram', 'milligramme', 'g', 'gram', 'gramme', 'kg', 'kilogram', 'kilogramme',
    # Lengths
    'in', 'inch',
    'cm', 'centimeter', 'centimetre'
    ]
# If a word is in this list, we consider it a cooking tool/implement.
tools = [
    'spoon', 'bowl', 'skillet', 'oven', 'knife', 'whisk', 'fork',
    'cutting board', 'can opener', 'strainer', 'sieve', 'blender', 'pan', 'pot',
    'saucepan', 'peeler', 'measuring cup', 'scoop', 'measuring spoon',
    'colander', 'masher', 'salad spinner', 'grater', 'shears', 'rolling pin',
    'juicer', 'garlic press', 'dish', 'plate', 'platter', 'foil', 'stockpot',
    'crockpot', 'spatula', 'tongs', 'ladle', 'trivet', 'lid', 'splatter guard',
    'paper towel', 'thermometer', 'scale', 'parchment paper', 'baking sheet',
    'glass', 'cup', 'tray', 'microwave', 'stove', 'stovetop', 'kettle',
    'toaster', 'chopper', 'double boiler', 'steamer'
    ]
# Used to help conversion from non-vegetarian to vegetarian
meat_products = [
    'beef', 'chicken', 'pork', 'bacon', 'sausage', 'ham', 'lamb', 'meat',
    'venison', 'veal', 'steak', 'ribs', 'filet mignon', 'shrimp', 'snail',
    'oyster', 'fish', 'tilapia', 'tuna', 'salmon', 'walleye', 'mussels',
    'pepperoni', 'salami', 'patty', 'turkey', 'duck', 'goat', 'liver'
    ]
# Maps meat products to suitable vegetarian replacements
veggie_replacements = {
    'seitan': ['chicken', 'pork', 'filet mignon', 'steak', 'venison', 'lamb', 'meat', 'ribs', 'turkey'],  # beef
    'tempeh': ['fish', 'tilapia', 'tuna', 'salmon', 'walleye']
    }
# Used to help convert from non-vegan to vegan
other_animal_products = [
    'milk', 'butter', 'cheese', 'honey', 'yogurt', 'sour cream', 'buttermilk',
    'mayonnaise', 'gelatin', 'ice cream', 'chocolate', 'sugar', 'egg'
    ]
# Maps non-vegan products to vegan replacements
vegan_replacements = {
    'margarine': ['butter'],
    'coconut milk': ['sour cream'],
    'coconut cream': ['yogurt'],
    'vegan gourmet cheese': ['cheese'],
    'cashew buttermilk': ['buttermilk'],
    'agar flakes': ['gelatin'],
    'sweetener': ['honey'],
    'soy milk': ['milk'],
    'cube(s) of tofu': ['egg'],
    'olive oil': ['butter'],
    'fructose': ['sugar'],
    'cocoa powder': ['chocolate'],
    'sorbet': ['ice cream'],
    'black beans': ['beef', 'chicken'],
    'seitan': ['chicken', 'pork', 'filet mignon', 'steak', 'venison', 'lamb', 'meat', 'ribs', 'turkey'],  # beef
    'tempeh': ['fish', 'tilapia', 'tuna', 'salmon', 'walleye']
}
# Used to help conversion from unhealthy to healthy
unhealthy_products = [
    'butter', 'canola oil', 'vegetable oil', 'bacon', 'chicken', 'beef', 'pork',
    'venison', 'noodles', 'pasta', 'rice', 'couscous', 'croutons', 'salt'
]
# Maps unhealthy products to suitable healthy replacements
healthy_replacements = {  # Buckwheat?
    'coconut butter': ['butter'],
    'coconut oil': ['canola oil', 'vegetable oil'],
    'prosciutto': ['bacon'],
    'turkey': ['chicken'],
    'venison': ['beef', 'pork'],
    'zoodles': ['noodles', 'pasta'],
    'quinoa': ['rice', 'couscous'],
    'nuts': ['croutons'],
    'garlic powder': ['salt'],
    'greek yogurt': ['sour cream'],
    'kale': ['lettuce'],
    'skim milk': ['milk']
}
# Used to help conversion from healthy to unhealthy
healthy_products = [
    'coconut butter', 'coconut oil', 'margarine', 'olive oil', 'vegetable oil',
    'applesauce', 'sweetener', 'date', 'honey', 'cauliflower', 'broccoli',
    'bread', 'yogurt', 'cream', 'rice', 'quinoa', 'couscous', 'water', 'milk'
    ]
# Maps healthier foods to suitable unhealth replacements
unhealthy_replacements = {
    'butter': ['coconut butter', 'margarine', 'olive oil'],
    'canola oil': ['coconut oil', 'vegetable oil'],
    'sugar': ['applesauce', 'sweetener', 'date', 'honey'],
    'sour cream': ['yogurt', 'cream'],
    'potatoes': ['cauliflower', 'broccoli'],
    'cheese': [],
    'white bread': ['bread'],
    'white rice': ['rice', 'quinoa', 'couscous'],
    'soda': ['water'],
    'whole milk': ['milk']
}
# Indian conversion
indian_spices = [
    'cumin', 'turmeric', 'paprika', 'cardamom', 'masala', 'cinnamon', 'cloves'
]
indian_food = [
    'naan', 'paratha'
]
# Ethiopian conversion
ethiopian_spices = [
    'fenugreek', 'new mexico chiles', 'paprika', 'nutmeg', 'cloves', 'onion powder'
]
ethiopian_food = [
    'injera'
]
# Spanish conversion
nonspanish_foods = [
    'beef', 'turkey', 'sausage', 'cinnamon', 'pepper', 'cumin', 'oregano',
    'parsley', 'mint', 'sauce', 'potatoes', 'chips', 'rice', 'bread'
]
spanish_replacements = {
    'jamon': ['beef', 'turkey'],
    'chorizo': ['sausage'],
    'pimentón': ['cinnamon'],
    'jalepeños': ['pepper'],
    'achiote': ['cumin'],
    'coriander': ['oregano'],
    'bay leaves': ['parsley', 'mint'],
    'guacamole sauce': ['sauce'],
    'corn': ['potatoes'],
    'corn chips': ['chips'],
    'red rice': ['rice'],
    'tortillas': ['bread']
}

thai_spices = ['garlic', 'chopped shallots', 'red chilis', 'galangal', 'basil', 'kaffir lime leaves']

ukrainian_spices = ['chives', 'thyme', 'dill', 'caraway', 'parsley']
ukrainian_foods = ['borsch']


class Step:
    def __init__(self, text):
        self.text = "You " + text.strip()[0:1].lower() + text.strip()[1:]
        nlp = spacy.load('en_core_web_sm')
        self.tokens = nlp(self.text)
        self.__parse__()
        self.__get_time()

    def __parse__(self):
        """First-time parse through a given step's text. Parsing attempts to
        extract a list of ingredients from the text of the recipe, as well as
        cooking verbs and tools. If an ingredient is found, its location is
        also saved for later substitutions.
        """
        self.ingredients = []
        self.locations = {}
        for i in range(len(self.tokens)):
            if (not self.tokens[i].tag_.startswith('NN')) or self.tokens[i].text in measurements_list:
                continue
            for key in ingredients.keys():
                ingredient = key
                if self.tokens[i].text.lower() in ingredient.lower() \
                   or \
                   (self.tokens[i].text.lower()[:-1] in ingredient.lower() and self.tokens[i].text.lower()[-1] == 's'):
                    potential_ingredient = self.tokens[i].text
                    j = i - 1
                    while j >= 0 and self.tokens[j].text.lower() in ingredient.lower():
                        potential_ingredient = self.tokens[j].text + " " + potential_ingredient
                        j -= 1
                    self.ingredients.append(potential_ingredient)
                    self.locations[potential_ingredient] = (j + 1, i)
        removals = []
        for i in range(len(self.ingredients)):
            for j in range(i+1, len(self.ingredients)):
                if self.ingredients[i] in self.ingredients[j]:
                    removals.append(i)
                elif self.ingredients[j] in self.ingredients[i]:
                    removals.append(j)
        self.ingredients = [self.ingredients[i] for i in range(len(self.ingredients)) if i not in removals]
        for i in range(len(self.ingredients)):
            prev = self.ingredients[i]
            self.ingredients[i] = find_largest_intersection(self.ingredients[i])
            if self.ingredients[i]:
                self.locations[self.ingredients[i]] = self.locations[prev]
        for loc_key in list(self.locations):
            if loc_key not in self.ingredients:
                del self.locations[loc_key]
        self.ingredients = [i for i in self.ingredients if i]
        self.verbs = []
        self.tools = []
        for token in self.tokens:
            if token.tag_ in ["VB", "VBP", "VBZ"] and token.text not in to_be_verbs and token.text in cooking_verbs:
                self.verbs.append(token)
            elif token.text in tools:
                self.tools.append(token.text)

    def __get_time(self):
        """Steps through the tokens of the step, searching for units of time.
        If one is found, it is paired with the last seen cooking verb, and
        the cooking verb paired with the longest timespan becomes our primary
        cooking method for this step.
        """
        self.time = 0
        self.primary_method = ''
        last_verb = ''
        for i in range(len(self.tokens)):
            if self.tokens[i].text.lower() in cooking_verbs:
                last_verb = self.tokens[i].text
            if self.tokens[i].tag_ in ['CD', 'LS'] or self.tokens[i].text == 'an':
                unit = self.tokens[i + 1].text
                if unit == 'hours':
                    try:
                        t = int(Fraction(self.tokens[i].text)) * 60
                        if t > self.time:
                            self.time = t
                            self.primary_method = last_verb
                    except Exception as e:
                        print(self.tokens[i].text)
                if unit == 'hour':
                    t = 60
                    if t > self.time:
                        self.time = t
                        self.primary_method = last_verb
                if unit == 'minutes':
                    try:
                        t = int(Fraction(self.tokens[i].text))
                        if t > self.time:
                            self.time = t
                            self.primary_method = last_verb
                    except Exception as e:
                        print(self.tokens[i].text)

    def get_tools(self):
        return self.tools

    def get_verbs(self):
        return [v.text for v in self.verbs]


def find_largest_intersection(ingredient):
    ingredient_set = set(ingredient.split())
    largest_intersection = 0
    real_ingredient = None
    for key in ingredients:
        each = key
        real_set = set(each.lower().replace(',', ' ').split())
        intersect = len(ingredient_set.intersection(real_set))
        if intersect > largest_intersection:
            largest_intersection = intersect
            real_ingredient = each
    return real_ingredient


def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2 and len(value) > 2]
    if len(lst3) > 0:
        print("intersection: " + str(lst3))
    return lst3


def get_recipe(in_url):
    """Given a url for an AllRecipes page,
    open the page and prepare for parsing.
    """
    global url
    global soup
    global recipe_name
    if in_url == '-1':
        url = base_url + str(random.randint(60_000, 250_000))
        print(url)
    else:
        url = in_url
    try:
        page = urlopen(url)
        soup = BeautifulSoup(page, 'html.parser')
        recipe_name = soup.find('h1', {'id': 'recipe-main-content'}).text
    except Exception as e:
        print('Failed to open recipe: ' + url)
        print(e)
        sys.exit(1)


def get_ingredients():
    """Iterates through each item in the ingredients section of the recipe
    page, extracting useful information including quantity and units, as well
    as descriptions of ingredients which may modify the ingredient, and
    preparation actions which need to be done before starting the recipe.
    """
    global ingredients
    checklist_items = soup.find_all(class_='checkList__line')[0:-3]
    nlp = spacy.load('en_core_web_sm')
    for item in checklist_items:
        text = item.text.strip()
        tokens = nlp(text)
        descriptor = []
        preparation = []
        name = []
        sum = 0
        product = 1
        posn = 0
        cutoff = len(tokens)
        for i in range(len(tokens)):
            # Removing 'such as ...'
            if i + 1 < len(tokens):
                if tokens[i].text == '(' and tokens[i+1].text == 'such':
                    cutoff = i
                    break
            # Quantities
            # Special care has been given to ingredients of the form
            # '3 (12 oz) can ...'
            # We parse this as 3 * 12 = '36 oz can ...'
            if tokens[i].tag_ in ['CD', 'LS'] and tokens[i + 1].text != '(':
                try:
                    sum += float(Fraction(tokens[i].text))
                    posn = i
                except Exception as e:
                    descriptor.append(i)
            elif tokens[i].tag_ in ['CD', 'LS'] and tokens[i + 1].text == '(':
                try:
                    product = float(Fraction(tokens[i].text))
                    posn = i
                except Exception as e:
                    descriptor.append(i)
            # Descriptors
            elif tokens[i].tag_.startswith('JJ') and tokens[i].dep_ not in ['nsubj', 'dobj', 'pobj']:
                descriptor.append(i)
            # Prep steps
            elif tokens[i].tag_ in ['VBN', 'RB']:
                preparation.append(i)
        product = sum * product
        potential_unit = tokens[posn + 1] if posn + 1 < len(tokens) else tokens[posn]
        if not potential_unit.tag_.startswith('JJ'):
            unit = potential_unit.text if is_unit(potential_unit.text) else ''
        else:
            second_unit = potential_unit.head.text
            unit = (potential_unit.text + ' ' + second_unit) if is_unit(second_unit) else ''
            posn += 1 if unit else 0
        if posn + 2 < len(tokens) and tokens[posn + 2].text == ')':
            posn += 2
        name = ''
        desc = ''
        prep = ''
        for i in range(posn + (2 if unit else 1), cutoff):
            if i in descriptor:
                desc += tokens[i].text + ' '
            elif i in preparation:
                prep += tokens[i].text + ' '
            elif tokens[i].text not in ['or', 'and', ',']:
                name += tokens[i].text + ' '
        name = name.strip()
        desc = desc.strip()
        prep = prep.strip()
        # 0: quantity 1: unit 2: description 3: prep step 4: name
        ingredients[text] = (product if product > 0 else None, unit, desc, prep, name, 0)
    return ingredients


def is_unit(text):
    """Given a string, determines if the string represents
    a unit of measurement in the context of cooking.
    """
    if text in measurements_list or text[0:-1] in measurements_list or (len(text) > 2 and text[0:-2] in measurements_list):
        return True
    return False


def get_instructions():
    """Splits a recipe on each sentence, so that we can regard
    each individual sentence as a separate step in our recipe.
    """
    instructions = soup.find_all(class_='recipe-directions__list--item')[0:-1]
    steps = []
    for instruct in instructions:
        text = instruct.text.strip().split('.')
        # AllRecipes sometimes puts videos on the page, so skip these
        steps += [Step(t) for t in text if len(t) > 0 and 'Watch Now' not in t]
    return steps


def get_primary_method(steps):
    """Check each step in our recipe, and try to find a cooking
    action that is paired with the longest span of time in our recipe.
    """
    max = 0
    max_step = "0"
    stepnum = None
    for ind, step in enumerate(steps):
        if step.primary_method == '':
            continue
        if step.time > max:
            max = step.time
            max_step = step.primary_method
            stepnum = ind
        elif step.time == max:
            if max_step in primary_verbs:
                continue
            max_step = step.primary_method
            stepnum = ind
    # We failed to a primary cooking method paired with a time, so use
    # a heirarchy of cooking verbs to determine the most important one
    if max_step == "0":
        for verb in reversed(primary_verbs):
            for ind, step in enumerate(steps):
                if verb in step.text:
                    max_step = verb
                    stepnum = ind
    return (max_step, stepnum)


def convert_to_vegetarian(ingredients, steps):
    """Converts a recipe to vegetarian.
    """
    veg_ingredients = {}
    modified_ingredients = {}
    for ingredient in ingredients:
        veg_ingredients[ingredient] = ingredients[ingredient]
        # Special case for vegetarian/vean recipes: we can't just replace chicken broth with tofu broth
        if 'soup' in ingredients[ingredient][4] or 'broth' in ingredients[ingredient][4]:
            for meat in meat_products:
                if meat in ingredient and '-flavo' not in ingredient:
                    replacement = "cream of mushroom soup" if 'cream' in ingredients[ingredient][4] else "vegetable broth"
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
        else:
            for meat in meat_products:
                if meat in ingredient and '-flavo' not in ingredient:
                    replacement = "tofu"
                    for veggie in veggie_replacements:
                        if meat in veggie_replacements[veggie]:
                            replacement = veggie
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
    for m_key, mod in modified_ingredients.items():
        veg_ingredients[m_key] = mod
    display_recipe(veg_ingredients, steps, 'Vegetarian ')


def convert_from_vegetarian(ingredients, steps):
    """Converts a recipe to non-vegetarian.
    """
    nonveg_ingredients = {}
    modified_ingredients = {}
    vegetarian_foods = [*veggie_replacements]
    vegetarian_foods.append('tofu')
    addBacon = True
    for ingredient in ingredients:
        nonveg_ingredients[ingredient] = ingredients[ingredient]
        if 'broth' in ingredient:
            replacement = 'chicken broth'
            modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
        else:
            for veggie in vegetarian_foods:
                if veggie in ingredient:
                    addBacon = False
                    replacement = "beef"
                    if veggie in veggie_replacements:
                        replacement = veggie_replacements[veggie][0]
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
    for m_key, mod in modified_ingredients.items():
        nonveg_ingredients[m_key] = mod
    display_recipe(nonveg_ingredients, steps, 'Non-Vegetarian ', addBacon=addBacon)


def convert_to_healthy(ingredients, steps):
    """Makes a recipe healthy.
    """
    healthy_ingredients = {}
    modified_ingredients = {}
    for ingredient in ingredients:
        healthy_ingredients[ingredient] = ingredients[ingredient]
        for unhealthy in unhealthy_products:
            if unhealthy in ingredient and 'broth' not in ingredient and 'soup' not in ingredient and '-flavo' not in ingredient:
                replacement = None
                for healthy in healthy_replacements:
                    if unhealthy in healthy_replacements[healthy]:
                        replacement = healthy
                if replacement:
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
    for m_key, mod in modified_ingredients.items():
        healthy_ingredients[m_key] = mod
    display_recipe(healthy_ingredients, steps, 'Healthy ')


def convert_from_healthy(ingredients, steps):
    """Converts a recipe to unhealhty.
    """
    unhealth_ingredients = {}
    modified_ingredients = {}
    sprinklecheese = True
    for ingredient in ingredients:
        unhealth_ingredients[ingredient] = ingredients[ingredient]
        for meat in meat_products:
            if meat in ingredient and 'broth' not in ingredient and '-flavo' not in ingredient and 'soup' not in ingredient:
                replacement = "deep fried " + ingredients[ingredient][4]
                modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
                sprinklecheese = False
                continue
        for healthy in healthy_products:
            if healthy in ingredient and 'heavy' not in ingredient:
                replacement = None
                for unhealthy in unhealthy_replacements:
                    if healthy in unhealthy_replacements[unhealthy]:
                        replacement = unhealthy
                if replacement:
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
    for m_key, mod in modified_ingredients.items():
        unhealth_ingredients[m_key] = mod
    display_recipe(unhealth_ingredients, steps, 'Unhealthy ', addCheese=sprinklecheese)


def convert_to_indian(ingredients, steps):
    """Converts to Indian cuisine.
    """
    modified_ingredients = {}
    indian_ingredients = {}
    for ingredient in ingredients:
        indian_ingredients[ingredient] = ingredients[ingredient]
        for meat in meat_products:
            if meat in ingredient and '-flavo' not in ingredient and 'broth' not in ingredient and 'soup' not in ingredient:
                modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, random.choice(["lamb", 'chicken']))
    text_set = soup.find_all(class_='recipe-ingredients')[0].text.lower()
    for spice in indian_spices:
        if spice not in text_set:
            modified_ingredients[spice] = (1, 'teaspoon', '', '', spice, 1)
    for m_key, mod in modified_ingredients.items():
        indian_ingredients[m_key] = mod
    display_recipe(indian_ingredients, steps, 'Indian Version of ', addNaan=True)


def convert_to_thai(ingredients, steps):
    """Converts to Thai cuisine.
    """
    modified_ingredients = {}
    thai_ingredients = {}
    for ingredient in ingredients:
        thai_ingredients[ingredient] = ingredients[ingredient]
        for meat in meat_products:
            if meat in ingredient and '-flavo' not in ingredient and 'soup' not in ingredient and 'broth' not in ingredient:
                modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, 'beef')
    text_set = soup.find_all(class_='recipe-ingredients')[0].text.lower()
    for spice in thai_spices:
        if spice not in text_set:
            modified_ingredients[spice] = (1, 'teaspoon', '', '', spice, 1)
    for m_key, mod in modified_ingredients.items():
        thai_ingredients[m_key] = mod
    display_recipe(thai_ingredients, steps, 'Thai Version of ', addThai=True)


def convert_to_ethiopian(ingredients, steps):
    """Converts to Ethiopian cuisine.
    """
    modified_ingredients = {}
    ethiopian_ingredients = {}
    for ingredient in ingredients:
        ethiopian_ingredients[ingredient] = ingredients[ingredient]
        for meat in meat_products:
            if meat in ingredient and '-flavo' not in ingredient and 'soup' not in ingredient and 'broth' not in ingredient:
                modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, 'chicken')
    text_set = soup.find_all(class_='recipe-ingredients')[0].text.lower()
    for spice in ethiopian_spices:
        if spice not in text_set:
            modified_ingredients[spice] = (1, 'teaspoon', '', '', spice, 1)
    for m_key, mod in modified_ingredients.items():
        ethiopian_ingredients[m_key] = mod
    display_recipe(ethiopian_ingredients, steps, 'Ethiopian Version of ', addInjera=True)


def convert_to_spanish(ingredients, steps):
    """Converts to Spanish cuisine.
    """
    modified_ingredients = {}
    spanish_ingredients = {}
    addJalepenos = True
    addCheese = True
    hasBayLeaf = False
    for ingredient in ingredients:
        spanish_ingredients[ingredient] = ingredients[ingredient]
        if 'bay lea' in ingredient:
            hasBayLeaf = True
        for nonspanish_food in nonspanish_foods:
            if nonspanish_food in ingredient and 'broth' not in ingredient and 'soup' not in ingredient:
                if not addJalepenos:
                    addCheese = False
                addJalepenos = False
                replacement = None
                for spanish_food in spanish_replacements:
                    if nonspanish_food in spanish_replacements[spanish_food]:
                        replacement = spanish_food
                modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
    for m_key, mod in modified_ingredients.items():
        if 'bay leaves' in mod and hasBayLeaf:
            continue
        spanish_ingredients[m_key] = mod
    display_recipe(spanish_ingredients, steps, 'Hispanic Version of ', addCheese=addCheese, addJalepenos=addJalepenos)


def convert_to_ukrainian(ingredients, steps):
    """Converts to Ukranian cuisine.
    """
    modified_ingredients = {}
    ukrainian_ingredients = {}
    for ingredient in ingredients:
        ukrainian_ingredients[ingredient] = ingredients[ingredient]
        for meat in meat_products:
            if meat in ingredient and '-flavo' not in ingredient and 'soup' not in ingredient and 'broth' not in ingredient:
                modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, 'duck')
    text_set = soup.find_all(class_='recipe-ingredients')[0].text.lower()
    for spice in ukrainian_spices:
        if spice not in text_set:
            modified_ingredients[spice] = (1, 'teaspoon', '', '', spice, 1)
    for m_key, mod in modified_ingredients.items():
        ukrainian_ingredients[m_key] = mod
    display_recipe(ukrainian_ingredients, steps, 'Ukrainian Version of ', addBorsch=True)


def convert_to_vegan(ingredients, steps):
    """Converts a recipe to vegan.
    """
    vegan_ingredients = {}
    modified_ingredients = {}
    for ingredient in ingredients:
        vegan_ingredients[ingredient] = ingredients[ingredient]
        # Special case for vegetarian/vean recipes: we can't just replace chicken broth with tofu broth
        if 'soup' in ingredient or 'broth' in ingredient:
            for meat in meat_products:
                if meat in ingredient and '-flavo' not in ingredient:
                    replacement = "cream of mushroom soup" if 'cream' in ingredients[ingredient][4] else "vegetable broth"
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
        else:
            for meat in meat_products:
                if meat in ingredient and '-flavo' not in ingredient:
                    replacement = "tofu"
                    for veggie in veggie_replacements:
                        if meat in veggie_replacements[veggie]:
                            replacement = veggie
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
            for prod in other_animal_products:
                if prod in ingredient:
                    replacement = "vegan " + ingredients[ingredient][4]
                    for rep in vegan_replacements:
                        if prod in vegan_replacements[rep]:
                            replacement = rep
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
    for m_key, mod in modified_ingredients.items():
        vegan_ingredients[m_key] = mod
    display_recipe(vegan_ingredients, steps, 'Vegan ')


def convert_from_vegan(ingredients, steps):
    """Converts a recipe from vegan.
    """
    nonvegan_ingredients = {}
    modified_ingredients = {}
    vegan_foods = [*vegan_replacements]
    vegan_foods.append('tofu')
    sprinklecheese = True
    for ingredient in ingredients:
        nonvegan_ingredients[ingredient] = ingredients[ingredient]
        if 'broth' in ingredient:
            replacement = 'chicken broth'
            modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
        else:
            for veg in vegan_foods:
                if veg in ingredient:
                    sprinklecheese = False
                    replacement = "beef"
                    if veg in vegan_replacements:
                        replacement = vegan_replacements[veg][0]
                    modified_ingredients = condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement)
    for m_key, mod in modified_ingredients.items():
        nonvegan_ingredients[m_key] = mod
    display_recipe(nonvegan_ingredients, steps, 'Non-Vegan ', addCheese=sprinklecheese)


def change_cooking_method(ingredients, steps):
    new_cooking_method = input("New cooking method: ")
    primary_method, index = get_primary_method(steps)
    new_steps = []
    for i, step in enumerate(steps):
        if i == index:
            new_steps.append(Step(step.text[4:].replace(primary_method, new_cooking_method)))
        else:
            new_steps.append(step)
    display_recipe(ingredients, new_steps, '')


def condense_ingredients(ingredients, ingredient, modified_ingredients, steps, replacement):
    """Given a tentative replacement during a transformation process, checks
    to ensure that the ingredient has not already been used. If it has, will
    condense the two to prevent duplication.
    """
    condense = None
    ambiguous = None
    # Check if this ingredient is already in the list of modified ingredients
    for m_key, mod in modified_ingredients.items():
        if mod[4] == replacement:
            condense = m_key
            break
    # If not, check if it's in the list of original ingredients
    if condense is None:
        for i_key, i in ingredients.items():
            if replacement in i[4]:
                condense = i_key
                ambiguous = i_key
                modified_ingredients[ambiguous] = (
                    ingredients[ambiguous][0],
                    ingredients[ambiguous][1],
                    ingredients[ambiguous][2],
                    ingredients[ambiguous][3],
                    ingredients[ambiguous][4],
                    1
                )
                break
    # If we indeed found a previous mention, make sure they're both always used in the same steps
    for step in steps:
        if (condense in step.ingredients) != (ingredient in step.ingredients):
            condense = None
            break
    # We need to condense the current ingredient into a previous one
    if condense is not None:
        amt1 = modified_ingredients[condense][0] if modified_ingredients[condense][0] is not None else 0
        unit1 = modified_ingredients[condense][1]
        amt2 = ingredients[ingredient][0] if ingredients[ingredient][0] is not None else 0
        unit2 = ingredients[ingredient][1]
        sum = amt1 + amt2
        sum_unit = unit1
        if unit2 == '':
            unit2 = unit1
        # Attempt unit conversion to add the ingredients together
        if unit1 != unit2:
            if unit1[-1] == 's':
                unit1 = unit1[:-1]
            if unit2[-1] == 's':
                unit2 = unit2[:-1]
            if unit1 == 'fluid ounce':
                unit1 = 'us_oz'
            if unit2 == 'fluid ounce':
                unit2 = 'us_oz'
            m = None
            try:
                m = guess(float(amt1), unit1, measures=[Weight, Volume])
            except Exception as e1:
                try:
                    m = guess(float(amt1), 'us_' + unit1, measures=[Weight, Volume])
                except Exception as e2:
                    pass
            s = None
            try:
                s = guess(float(amt2), unit2, measures=[Weight, Volume])
            except Exception as e1:
                try:
                    s = guess(float(amt2), 'us_' + unit2, measures=[Weight, Volume])
                except Exception as e2:
                    pass
            if m is not None and s is not None:
                type1 = None
                type2 = None
                try:
                    m.oz
                    type1 = 'weight'
                except Exception as e:
                    type1 = 'volume'
                try:
                    s.oz
                    type2 = 'weight'
                except Exception as e:
                    type2 = 'volume'
                if type1 == type2 == 'weight':
                    sum_unit = 'oz'
                    sum = m.oz + s.oz
                elif type1 == type2 == 'volume':
                    sum_unit = 'fl oz'
                    sum = m.us_oz + s.us_oz
                elif type1 == 'weight' and type2 == 'volume':
                    sum_unit = 'ounces'
                    sum = m.oz + s.us_oz
                elif type1 == 'volume' and type2 == 'weight':
                    sum_unit = 'ounces'
                    sum = m.us_oz + s.oz
        modified_ingredients[condense] = (
            sum,
            sum_unit,
            '',
            '',
            modified_ingredients[condense][4],
            1
        )
        modified_ingredients[ingredient] = (-1, None, None, None, condense, 1)
    # We can just go ahead and add this new ingredient
    else:
        modified_ingredients[ingredient] = (
            ingredients[ingredient][0],
            ingredients[ingredient][1],
            '',
            '',
            replacement,
            1
        )
    return modified_ingredients


def display_recipe(ingredients, steps, style, addBacon=False, addCheese=False, addNaan=False, addInjera=False, addJalepenos=False, addBorsch=False, addThai=False):
    """Given a set of ingredients and steps,
    display them in a nice way to the user.
    """
    # Print the list of ingredients
    print(style + recipe_name + "\n")
    for external_rep, internal_rep in ingredients.items():
        if internal_rep[-1] == 0:
            print(external_rep)
        else:
            line = ''
            if internal_rep[0] == -1:
                continue
            for i in internal_rep[:-1]:
                line += ((str(i).strip() + ' ') if i else '')
            print(line)
        # Reveal our internal representations
        if debug:
            line = ''
            for i in internal_rep:
                line += ((str(i).strip() + ' | ') if i else '_ | ')
            print(line)
    # If we need an extra ingredient to add to the authenticity of a conversion, print it here
    if addBacon:
        print("Bacon bits, to taste")
    if addCheese:
        print('Shredded cheese, to taste')
    if addNaan:
        print('Naan bread, as many as you prefer')
    if addInjera:
        print('Injera, as much as you prefer')
    if addJalepenos:
        print('Sliced jalepeños, to taste')
    if addBorsch:
        print('A cup of borsch as an appetizer')
    print()
    primary_method, method_index = get_primary_method(steps)
    # Print recipe steps
    # If we need extra steps to prepare authentic ingredients, prepare them here
    if addNaan:
        print('Step 0: Prepare a mixture of the cumin, turmeric, paprika, cardamom, masala, cinnamon, and cloves for later use\n')
    if addInjera:
        print('Step 0: To prepare berbere sauce for use later, mix fenugreek, new mexico chiles, paprika, nutmeg, cloves, and onion powder\n')
    if addThai:
        print('Step 0: Prepare a mixture of the garlic, chopped shallots, red chilis, galangal, basil, and kaffir lime leaves\n')
    if addBorsch:
        print('Step 0: Prepare borsch (purchased from a Ukrainian deli) and prepare mixture of chive, dill, thyme, caraway, parsley\n')
    for x in range(len(steps)):
        modified = False
        for i in steps[x].ingredients:
            if ingredients[i][-1] == 1:
                modified = True
                break
        # We can just print the original steps
        if not modified:
            line = ''
            if (addNaan or addThai) and x == method_index:
                line = ', adding in spices from Step 0'
            if addInjera and x == method_index:
                line = ', adding in the berbere sauce from Step 0'
            if addJalepenos and x == method_index:
                line = ', adding in the sliced jalepeños from Step 0'
            if addBorsch and x == method_index:
                line = ', adding in spices from Step 0'
            print('Step ' + str(x + 1) + ': ' + str(steps[x].text[4:5].upper()) + str(steps[x].text[5:]) + line)
        # We must print the step with substitutions
        else:
            tokens = steps[x].tokens
            locations = steps[x].locations
            # Skip the word "You"
            i = 2
            line = 'Step ' + str(x + 1) + ': ' + str(tokens[1].text[0:1].upper()) + str(tokens[1].text[1:]) + ' '
            while i < len(tokens):
                breaker = False
                for loc in locations:
                    if i == locations[loc][0]:
                        if ingredients[loc][-1] == 0:
                            break
                        i = locations[loc][1] + 1
                        if ingredients[loc][0] == -1:
                            if tokens[locations[loc][0] - 1].text == ',':
                                line = line[0:-2] + ' '
                            elif tokens[locations[loc][0] - 1].text == 'and':
                                line = line[0:-4]
                                if tokens[locations[loc][0] - 2].text == ',':
                                    line = line[0:-2] + ' '
                            elif tokens[i].text == ',':
                                i = i + 1
                            elif tokens[i].text == 'and':
                                i = i + 1
                            breaker = True
                            break
                        for t in ingredients[loc][:-1]:
                            line += ((str(t).strip() + ' ') if t else '')
                        breaker = True
                        break
                if i == len(tokens) or breaker:
                    continue
                if tokens[i].text in [',', '.', ';']:
                    line = line[0:-1]
                line += tokens[i].text + ' '
                i += 1
            if x == method_index and (addNaan or addThai):
                line = line.strip()
                line += ', adding in the prepared spices from Step 0'
            if x == method_index and addInjera:
                line = line.strip()
                line += ', adding in the berbere sauce from Step 0'
            if addJalepenos and x == method_index:
                line = line.strip()
                line += ', adding in the sliced jalepeños from Step 0'
            if x == method_index and addBorsch:
                line = line.strip()
                line += ', adding in the spices from Step 0'
            print(line)
        # Reveal our internal representations
        if debug:
            print('\tActions: ' + ', '.join(steps[x].get_verbs())) if steps[x].get_verbs() else 0
            print('\tTools: ' + ', '.join(steps[x].get_tools())) if steps[x].get_tools() else 0
            print('\tIngredients: ' + ', '.join(steps[x].ingredients)) if steps[x].ingredients else 0
            print('\tMethod: ' + steps[x].primary_method + ' %d minutes' % steps[x].time) if steps[x].primary_method else 0
        print()
    if addBacon:
        print('Step ' + str(len(steps) + 1) + ': Sprinkle on bacon bits. Enjoy!\n')
    if addCheese:
        print('Step ' + str(len(steps) + 1) + ': Sprinkle on cheese. Enjoy!\n')
    if addNaan:
        print('Step ' + str(len(steps) + 1) + ': Eat with Naan. Enjoy!\n')
    if addInjera:
        print('Step ' + str(len(steps) + 1) + ': Serve with Injera. Enjoy!\n')
    if addBorsch:
        print('Step ' + str(len(steps) + 1) + ': Serve with Borsch. Enjoy!\n')
    print('Primary cooking method is: ' + primary_method)


if __name__ == "__main__":
    get_recipe(sys.argv[1] if (len(sys.argv) > 1) else urls[0])
    ingredients = get_ingredients()
    steps = get_instructions()
    val = '0'
    while val != 'q':
        # Used to change debug flag
        if val == '~':
            debug = not debug
            val = '0'
        # Difficulty level 1
        if val == 'D1':
            val = '0'
        # Difficulty level 2
        elif val == 'D2':
            val = '0'
        # Difficulty level 3
        elif val == 'D3':
            val = '0'
        # Show original Recipe
        elif val == '0':
            display_recipe(ingredients, steps, '')
        # Make a non-vegetarian recipe vegetarian
        elif val == '1':
            convert_to_vegetarian(ingredients, steps)
        # Make a vegetarian recipe non-vegetarian
        elif val == '2':
            convert_from_vegetarian(ingredients, steps)
        # Make a recipe healthy
        elif val == '3':
            convert_to_healthy(ingredients, steps)
        # Make a recipe unhealth
        elif val == '4':
            convert_from_healthy(ingredients, steps)
        # Make a recipe Indian style
        elif val == '5':
            convert_to_indian(ingredients, steps)
        # Make a recipe Ethiopian style
        elif val == '6':
            convert_to_ethiopian(ingredients, steps)
        # Make a recipe Spanish style
        elif val == '7':
            convert_to_spanish(ingredients, steps)
        # Make a recipe Thai style
        elif val == '8':
            convert_to_thai(ingredients, steps)
        # Make a recipe Ukranian style
        elif val == '9':
            convert_to_ukrainian(ingredients, steps)
        # Make a recipe vegan
        elif val == '10':
            convert_to_vegan(ingredients, steps)
        # Make a vegan recipe non-vegan
        elif val == '11':
            convert_from_vegan(ingredients, steps)
        # Change the primary cooking method
        elif val == '12':
            change_cooking_method(ingredients, steps)
        # Invalid option
        else:
            print("Invalid option: " + val)
            display_recipe(ingredients, steps, '')
        val = input("""
0: Show Original Recipe
1: Convert to Vegetarian
2: Convert From Vegetarian
3: Convert to Healthy Style
4: Convert from Healthy Style
5: Convert to Indian Style
6: Convert to Ethiopian Style
7: Convert to Hispanic Style
8: Convert to Thai Style
9: Convert to Ukranian Style
10: Convert to Vegan
11: Convert from Vegan
12: Change cooking method
~: Toggle debug printing
Q: Quit\n>>""").strip().lower()
        os.system('cls') if platform.platform().lower().startswith('windows') else os.system('clear')
    print("Goodbye!")
