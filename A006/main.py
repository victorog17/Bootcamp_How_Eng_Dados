from selenium import webdriver
import sys
import time

#cep = sys.argv[1]

#if cep:
driver = webdriver.Chrome('.\src\chromedriver.exe')
time.sleep(2)

#Acesso ao site dos Correios
driver.get('https://buscacepinter.correios.com.br/app/endereco/index.php?t')
elem_cep = driver.find_element('name', 'endereco')
elem_cep.clear()
elem_cep.send_keys('12227600')

# Procurando CEP
elem_cmb = driver.find_element('name', 'tipoCEP')
elem_cmb.click()
driver.find_element('xpath', '//*[@id="tipoCEP"]/optgroup/option[6]')
driver.find_element('name', 'btn_pesquisar').click()

# Extraindo Informações do CEP
time.sleep(2)
logradouro = driver.find_element('xpath', '//*[@id="resultado-DNEC"]/tbody/tr/td[1]').text
time.sleep(0.5)
bairro = driver.find_element('xpath', '//*[@id="resultado-DNEC"]/tbody/tr/td[2]').text
time.sleep(0.5)
localidade = driver.find_element('xpath', '//*[@id="resultado-DNEC"]/tbody/tr/td[3]').text
time.sleep(0.5)
cep = driver.find_element('xpath', '//*[@id="resultado-DNEC"]/tbody/tr/td[4]').text

driver.close()

print(f"""
Para o CEP {cep} temos:

Endereço: {logradouro.split(' - ')[0]}
Bairro: {bairro}
Localidade: {localidade}
""")