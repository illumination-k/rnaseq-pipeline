# README.md

## USAGE

```bash
git clone https://github.com/illumination-k/rnaseq-pipeline.git
pip install -e .
# non root user
pip install --user -e .
```

## make salmon index

refer to [this tutorial](https://combine-lab.github.io/alevin-tutorial/2019/selective-alignment/)

```bash
grep "^>" genome.fa | cut -d " " -f 1 > decoys.txt
sed -i.bak -e 's/>//g' decoys.txt
cat mrna.fa genome.fa > salmon.fa
```

## datasource

### marchantia
marchantia info

### klebsormidium
http://www.plantmorphogenesis.bio.titech.ac.jp/~algae_genome_project/klebsormidium/index.html

### selaginella

https://phytozome-next.jgi.doe.gov/info/Smoellendorffii_v1_0

### physcomitrella

https://phytozome-next.jgi.doe.gov/info/Ppatens_v3_3
