#!/usr/bin/perl -w
use strict;
use LWP::Curl;
use File::Find::Rule;
use Log::Handler;

# Set up logging
my $log = Log::Handler->new();

$log->add(
	file => {
		filename => "/data/logs/wordpress-check.log",
		maxlevel => "debug",
		minlevel => "warning",
	}
);


# Wordpress file that contains version number.
my $file = 'wp-includes/version.php';

# Path to WordPress installs.
my $path = '/data/wordpress';

# Empty array for folders.
my @folders;

# New LWP::Curl object
my $curl = LWP::Curl->new();

# Get all the directory names for WordPress projects.
opendir DIR, $path;

while (my $wp = readdir(DIR)) {
	if ($wp !~ /^\./) {
		push(@folders, $wp);
	}
}

close DIR;

# Iterate through the projects
foreach my $wp_install (@folders) {

	my $current;

	# Read the version file.
	my $version_file = "$path/$wp_install/$file";
	open IN, "<$version_file";

	my @lines = <IN>;

	# Pull out the version number.
	foreach my $line (@lines) {
		if ($line =~ m/^\$wp_version/) {
			$current = $line;
			$current =~ s/(.*')(\d.*)('.*)/$2/;
		}
	}
	close IN;

	# Get the latest version from WordPress
	my $latest = $curl->get("http://api.wordpress.org/core/version-check/1.0/?version=$current");

	# If we have the latest version, the WordPress API call will return "latest".
	if ($latest eq 'latest') {
		$log->info($wp_install . ": We're all good.");
	}
	else {
		$log->warning($wp_install . ": Time to upgrade!");
	}
}
