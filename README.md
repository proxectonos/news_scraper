![ALIA Project](https://langtech-bsc.gitbook.io/alia-kit/~gitbook/image?url=https%3A%2F%2F798406309-files.gitbook.io%2F%7E%2Ffiles%2Fv0%2Fb%2Fgitbook-x-prod.appspot.com%2Fo%2Fspaces%252Fk1rmBoGwZe21EgkVbqEr%252Fuploads%252FHG0Arow2kpc28XAmZ3s2%252FLOGOALIA_POS_COLOR.png%3Falt%3Dmedia%26token%3D7d7cc93d-8cac-408d-a950-f5c7d189192b&width=768&dpr=4&quality=100&sign=c610ba&sv=2)

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
