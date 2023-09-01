# Australasian Evolution Society Website

![Australasian Evolution Society Logo](./img/AES_logo1.png)

Welcome to the GitHub repository for the **Australasian Evolution Society Website**. This repository houses the source code and assets for the official website of the Australasian Evolution Society (AES). 

## Table of Contents

- [About the Australasian Evolution Society](#about-the-australasian-evolution-society)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Contributing](#contributing)
- [License](#license)

## About the Australasian Evolution Society

The **Australasian Evolution Society** is a learned society founded in 1999. We are devoted to bringing evolutionary biologists together to promote intellectual exchange and to foster and advance evolutionary biology.  

Our Mission is to promote the scientific study of evolution, the discussion of the scientific findings of its members, and their dissemination to the wider public.

## Getting Started

To set up the AES website locally for development or testing purposes, follow the instructions below.

### Prerequisites

1.  Install Ruby. For more information, see "[Installing Ruby](https://www.ruby-lang.org/en/documentation/installation/)" in the Ruby documentation.
2.  Install Bundler. For more information, see "[Bundler](https://bundler.io/)."

-   Install [Jekyll](https://jekyllrb.com/docs/installation/).
We recommend using [Bundler](https://bundler.io/) to install and run Jekyll. Bundler manages Ruby gem dependencies, reduces Jekyll build errors, and prevents environment-related bugs. 

### Build your site locally 

The following instruction is for Windows but more information can be found at [Testing your Github Pages site locally with Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/testing-your-github-pages-site-locally-with-jekyll?platform=windows) from GitHub Pages.

-   Open Git Bash.
    
-   Navigate to the publishing source for your site. For more information, see "[Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)."
    
-   Run `bundle install`.
    
-   Run your Jekyll site locally with `$ bundle exec jekyll serve` 

-   To preview site in your browser navigate to `http://localhost:4000`

### Updating Github Pages gem 

-   In your Git Bash terminal run `bundle update github-pages`

### Deployment (and best practice) 

- Create a branch to work on changes of website locally. 
- Test with local build. 
- Once happy push the branch and request a merge request
- The repo has Actions that automatically build and deploys the site to aesevo.com 

### Contributing 

We welcome contributions from the AES community for news and blog posts! Please contact ausevolutionsociety@gmail.com.  

If you find any bugs, have suggestions for improvements please open an issue or submit a pull request.

## Contributors

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

