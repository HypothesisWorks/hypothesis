if !system('cargo --version')
  raise 'Hypothesis requires cargo to be installed (https://www.rust-lang.org/)'
end

require 'rake'
