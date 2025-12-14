# news_scraper

Operacionalización do acceso a corpus de texto para o treino de modelos en galego.


Coa opción `--help` obtense axuda.

```
$ python run.py --help
usage: run.py [-h] [--loglevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}] {praza,nosdiario} ...

News scraper

options:
  -h, --help            show this help message and exit
  --loglevel, -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Define o nivel de registo.

source:
  {praza,nosdiario}
    praza               Scraper de Praza Pública
    nosdiario           Scraper de Nós Diario
```

Tamén para os subcomandos:

```
$ python run.py praza --help
usage: run.py praza [-h]
                    [--category {Acontece,Ciencia e tecnoloxía,Cultura,Deportes,Economía,Lecer,Movementos sociais,Mundo,Política} [{Acontece,Ciencia e tecnoloxía,Cultura,Deportes,Economía,Lecer,Movementos sociais,Mundo,Política} ...]]
                    (--download [FROM] | --parse [FILE])

options:
  -h, --help            show this help message and exit
  --category, -c {Acontece,Ciencia e tecnoloxía,Cultura,Deportes,Economía,Lecer,Movementos sociais,Mundo,Política} [{Acontece,Ciencia e tecnoloxía,Cultura,Deportes,Economía,Lecer,Movementos sociais,Mundo,Política} ...]
                        Categorias para descarregar.
  --download, -d [FROM]
                        Descarregar os ficheiros HTML (FROM: [category, rss]; por defecto: 'category').
  --parse, -p [FILE]    Parsea todos os ficheiros HTML descarregados (FILE para processar só um
                        ficheiro).
```



## Praza Pública

Descarga os HTML de Praza Pública desde os inicios ate hoxe.

```
$ python run.py --loglevel INFO praza --download
```

Descarga só as categorías "Acontece" e "Ciencia e tecnoloxía".

```
python run.py --loglevel INFO praza --download --category Acontece "Ciencia e tecnoloxía"
```

Procesa os HTML para producir o JSON final.

```
$ python run.py --loglevel INFO praza --parse 
```

## NÓS Diario

Procesa os XML en formato NewsML descarregados previamente do RSS privado.

```
$ python run.py --loglevel INFO nosdiario --parse 
```
