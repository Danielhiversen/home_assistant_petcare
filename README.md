# Sure Petcare
![Validate with hassfest](https://github.com/Danielhiversen/home_assistant_adax/workflows/Validate%20with%20hassfest/badge.svg)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Custom component for using Sure Petcare flaps in Home Assistant. This is an alternative integration to the offical one: https://www.home-assistant.io/integrations/surepetcare/

This add support for locks and limit the number of unecessary requests to petcare as much as possible. It does not support feeders.

[Support the developer](http://paypal.me/dahoiv)

## Acknowledgments

* Thanks to [@benleb](https://github.com/benleb) for [https://github.com/benleb/surepy](https://github.com/benleb/surepy)
* Thanks to [@rcastberg](https://github.com/rcastberg) for [github.com/rcastberg/sure_petcare](https://github.com/rcastberg/sure_petcare)


## Install
Use [hacs](https://hacs.xyz/) (probably easier) or copy the files to the custom_components folder in Home Assistant (should be placed in the same folder as configuration.yaml) .

## Configuration (2 options)

You have two alternatives. 

Alternative 1:
Go to integration page in HA, press + and search for Petcare
Enter your email
Enter your password

Alternative 2:
In configuration.yaml:

```
petcare:
  username: mail@mail.com
  password: 'pswd'

```



[releases]: https://github.com/Danielhiversen/home_assistant_petcare/releases
[releases-shield]: https://img.shields.io/github/release/Danielhiversen/home_assistant_petcare.svg?style=popout
[downloads-total-shield]: https://img.shields.io/github/downloads/Danielhiversen/home_assistant_petcare/total
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg
[hacs]: https://hacs.xyz/docs/default_repositories
