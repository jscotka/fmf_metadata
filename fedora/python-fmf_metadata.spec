%global srcname fmf_metadata

Name:           python-%{srcname}
Version:        0.1.0
Release:        1%{?dist}
Summary:        Python library what helps you with FMF formatting

License:        MIT
URL:            https://github.com/jscotka/fmf_metadata
Source0:        %{pypi_source}
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3dist(pytest)
BuildRequires:  python3dist(pyyaml)
BuildRequires:  python3dist(setuptools)
BuildRequires:  python3dist(setuptools-scm)
BuildRequires:  python3dist(setuptools-scm-git-archive)

%description
Python library what helps you with FMF formatting via decorators and generate
FMF files for you

%package -n     python3-%{srcname}
Summary:        %{summary}

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/#_provides
%if 0%{?fedora} < 33
%{?python_provide:%python_provide python3-%{srcname}}
%endif

%description -n python3-%{srcname}
Python library what helps you with FMF formatting via decorators and generate
FMF files for you

%prep
%autosetup -n %{srcname}-%{version}
# Remove bundled egg-info
rm -rf %{srcname}.egg-info

%build
%py3_build

%install
%py3_install

%files -n python3-%{srcname}
%license LICENSE
%doc README.md
%{_bindir}/requre-patch
%{python3_sitelib}/%{srcname}
%{python3_sitelib}/%{srcname}-%{version}-py%{python3_version}.egg-info

%changelog
* Wed Feb 01 2021 Jan Ščotka <jscotka@redhat.com> - 0.1.0-1
- Initial package.
